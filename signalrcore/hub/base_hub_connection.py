import logging
import websocket
import threading
import uuid
import time

from signalrcore.messages.message_type import MessageType
from signalrcore.messages.stream_invocation_message\
    import StreamInvocationMessage

from signalrcore.messages.ping_message import PingMessage

from .reconnection import ConnectionStateChecker, ExponentialReconnectionHandler, RawReconnectionHandler, ReconnectionType

class StreamHandler(object):
    def __init__(self, event, invocation_id):
        self.event = event
        self.invocation_id = invocation_id
        self.next_callback = None
        self.complete_callback = None
        self.error_callback = None

    def subscribe(self, subscribe_callbacks):
        if subscribe_callbacks is None:
            raise ValueError(" subscribe object must be {0}".format({
                "next": None,
                "complete": None,
                "error": None
                }))
        self.next_callback = subscribe_callbacks["next"]
        self.complete_callback = subscribe_callbacks["complete"]
        self.error_callback = subscribe_callbacks["error"]


class BaseHubConnection(websocket.WebSocketApp):
    def __init__(self, url, protocol, headers={}):
        self.logger = logging.getLogger("SignalRCoreClient")
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        self.logger.addHandler(ch)
        self.url = url
        self.protocol = protocol
        self.headers = headers
        self.handshake_received = False
        self.connection_alive = False
        self.handlers = []
        self.stream_handlers = []
        self._thread = None
        self._ws = None
        self.connection_checker = ConnectionStateChecker(
            lambda: self.send(PingMessage()),
            15
        )
        self.reconnection_handler = None

    def start(self):
        self._ws = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
            )
        self._thread = threading.Thread(target=self._ws.run_forever)
        self._thread.daemon = True
        self._thread.start()
        self.connection_checker.start()

    def configure_reconnection(
            self,
            reconnection_type,
            keep_alive_interval=15,
            reconnect_interval=5,
            max_attemps=None):

        self.connection_checker.keep_alive_interval = keep_alive_interval

        reconn_type = ReconnectionType[reconnection_type]
        
        if reconn_type == ReconnectionType.raw:
            self.reconnection_handler = ReconnectionHandler(
                sleep_time = reconnect_interval,
                max_attemps = max_attemps
            )
        if reconn_type == ReconnectionType.exponential:
            self.reconnection_handler = ReconnectionHandler(
                sleep_time = reconnect_interval,
                max_attemps = max_attemps
            )
        


    def stop(self):
        if self.connection_alive:
            self.close()
        self.connection_checker.stop()

    def register_handler(self, event, callback):
        self.handlers.append((event, callback))

    def evaluate_handshake(self, message):
        msg = self.protocol.decode_handshake(message)
        if msg.error is None or msg.error == "":
            self.handshake_received = True
            self.connection_alive = True
            self.reconnection_handler.reconnecting = False
        else:
            self.logger.error(msg.error)
            raise ValueError("Handshake error {0}".format(msg.error))

    def on_open(self):
        self.logger.info("-- web socket open --")
        msg = self.protocol.handshake_message()
        self.send(msg)

    def on_close(self):
        self.logger.info("-- web socket close --")

    def on_error(self, error):
        self.logger.error("-- web socket error --")
        self.logger.error("{0} {1}".format(error, type(error)))

    def on_message(self, raw_message):
        self.connection_checker.last_message = time.time()
        if not self.handshake_received:
            self.evaluate_handshake(raw_message)
            return

        messages = self.protocol.parse_messages(raw_message)
        for message in messages:
            if message.type == MessageType.invocation_binding_failure:
                logging.error(message)
                continue
            if message.type == MessageType.ping:
                continue

            if message.type == MessageType.invocation:
                fired_handlers = list(
                    filter(
                        lambda h: h[0] == message.target,
                        self.handlers))
                if len(fired_handlers) == 0:
                    logging.warn(
                        "event '{0}' hasn't fire any handler".format(
                            message.target))
                for _, handler in fired_handlers:
                    handler(message.arguments)

            if message.type == MessageType.close:
                logging.info("Close message received from server")
                self.connection_alive = False
                return

            if message.type == MessageType.completion:
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))
                for handler in fired_handlers:
                    handler.complete_callback(message)

                # unregister handler
                self.stream_handlers = list(
                    filter(
                        lambda h: h.invocation_id != message.invocation_id,
                        self.stream_handlers))

            if message.type == MessageType.stream_item:
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))
                if len(fired_handlers) == 0:
                    logging.warn(
                        "id '{0}' hasn't fire any stream handler".format(
                            message.invocation_id))
                for handler in fired_handlers:
                    handler.next_callback(message.item)

            if message.type == MessageType.stream_invocation:
                pass

            if message.type == MessageType.cancel_invocation:
                fired_handlers = list(
                    filter(
                        lambda h: h.invocation_id == message.invocation_id,
                        self.stream_handlers))
                if len(fired_handlers) == 0:
                    logging.warn(
                        "id '{0}' hasn't fire any stream handler".format(
                            message.invocation_id))

                for handler in fired_handlers:
                    handler.error_callback(message)

                # unregister handler
                self.stream_handlers = list(
                    filter(
                        lambda h: h.invocation_id != message.invocation_id,
                        self.stream_handlers))

    def send(self, message):
        try:
            self._ws.send(self.protocol.encode(message))
            self.connection_checker.last_message = time.time()
        except (
                websocket._exceptions.WebSocketConnectionClosedException,
                ConnectionResetError) as ex:
            if self.reconnection_handler is None:
                raise ex
            # Connection closed
            self.logger.error("Connection closed {0}".format(ex))
            self.connection_alive = False
            if not self.reconnection_handler.reconnecting:
                self.reconnection_handler.reconnecting = True
                self.stop()
                self.start()

        except Exception as ex:
            raise ex

    def stream(self, event, event_params):
        invocation_id = str(uuid.uuid4())
        stream_obj = StreamHandler(event, invocation_id)
        self.stream_handlers.append(stream_obj)
        self.send(
            StreamInvocationMessage(
                {},
                invocation_id,
                event,
                event_params))
        return stream_obj
