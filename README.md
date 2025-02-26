# SignalR core client

![Pypi](https://img.shields.io/pypi/v/signalrcore.svg)
![Pypi - downloads month](https://img.shields.io/pypi/dm/signalrcore.svg)
![Issues](https://img.shields.io/github/issues/mandrewcito/signalrcore.svg)
![Open issues](https://img.shields.io/github/issues-raw/mandrewcito/signalrcore.svg)

# Example 

Using package from [aspnet core - SignalRChat](https://codeload.github.com/aspnet/Docs/zip/master) 
example chat without auth
```python

from signalrcore.hub_connection_builder import HubConnectionBuilder


def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


server_url = input_with_default('Enter your server url(default: {0}): ', "ws://localhost:62342/chathub")
username = input_with_default('Enter your username (default: {0}): ', "mandrewcito")

hub_connection = HubConnectionBuilder().with_url(server_url).build()
hub_connection.on("ReceiveMessage", print)
hub_connection.start()
message = None
# Do login

while message != "exit()":
    message = input(">> ")
    if message is not None and message is not "" and message is not "exit()":
        hub_connection.send("SendMessage", [username, message])
hub_connection.stop()


```

Using package from [aspnet core - SignalRAuthenticationSample](https://codeload.github.com/aspnet/Docs/zip/master) ,

# Example with Auth
```python
import requests
from signalrcore.hub_connection_builder import HubConnectionBuilder


def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


def signalr_core_example_login(url, user, username_password):
    response = requests.post(url, data={"email": user, "password": username_password})
    return response.json()["token"]


login_url = input_with_default('Enter your server login url({0}):', "http://localhost:50746/account/token")
server_url = input_with_default('Enter your server url(default: {0}): ', "ws://localhost:50746/hubs/chat")
username = input_with_default('Enter your username (default: {0}): ', "mandrewcito@mandrewcito.com")
password = input_with_default('Enter your password (default: {0}): ', "Abc123.--123?")

hub_connection = HubConnectionBuilder()\
    .with_url(server_url, options={
        "access_token_factory": lambda: signalr_core_example_login(login_url, username, password)
    })\
    .build()

hub_connection.on("ReceiveSystemMessage", print)
hub_connection.on("ReceiveChatMessage", print)
hub_connection.on("ReceiveDirectMessage", print)
hub_connection.start()
message = None
while message != "exit()":
    message = input(">> ")
    if message is not None and message is not "" and message is not "exit()":
        hub_connection.send("Send", [message])
hub_connection.stop()
```
# Example with streamming

Using package from [aspnet core - SignalRStreaming](https://codeload.github.com/aspnet/Docs/zip/master) ,

```python


import time
import sys
from signalrcore.hub_connection_builder import HubConnectionBuilder


def input_with_default(input_text, default_value):
    value = input(input_text.format(default_value))
    return default_value if value is None or value.strip() == "" else value


server_url = input_with_default('Enter your server url(default: {0}): ', "ws://localhost:57957/streamHub")

hub_connection = HubConnectionBuilder().with_url(server_url).build()
hub_connection.start()
time.sleep(10)


def bye(error, x):
    if error:
        print("error {0}".format(x))
    else:
        print("complete! ")
    global hub_connection
    hub_connection.stop()
    sys.exit(0)


hub_connection.stream(
    "Counter",
    [10, 500]).subscribe({
        "next": lambda x: print("next callback: ", x),
        "complete": lambda x: bye(False, x),
        "error": lambda x: bye(True, x)
    })

```
