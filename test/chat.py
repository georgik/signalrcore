
from signalrcore.hub_connection_builder import HubConnectionBuilder


def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


server_url = input_with_default('Enter your server url(default: {0}): ', "ws://localhost:62342/chathub")
username = input_with_default('Enter your username (default: {0}): ', "mandrewcito")

hub_connection = HubConnectionBuilder().with_url(server_url).build()
hub_connection.on_disconnect({
    "type":"raw",
    "keep_alive_interval":10,
    "reconnect_interval": 5,
    "max_attemps": 5
})
hub_connection.on("ReceiveMessage", print)
hub_connection.start()
message = None

# Do login

while message != "exit()":
    message = input(">> ")
    if message is not None and message is not "" and message is not "exit()":
        hub_connection.send("SendMessage", [username, message])

hub_connection.stop()