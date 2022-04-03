# sus-ui

A client for [among-foss](https://github.com/Raniconduh/among-foss)


## Usage

After starting the client (`likely via ./sus-ui.py`), enter the IP (or hostname) and port of the server you wish to connect to. Pressing enter (without entering anything else) will use the default hostname (`localhost`) and port (`1234`). If the client is able to connect to a server with the given information, you will be prompted to enter a username.

Now, unless a game is already started on the server, you will be put into the lobby. At this point, the client is usable as a basic chat app. Once ready, the server admin can start the game with the `/start` command. If the game can be started, each client will be told whether they are an imposter or crewmate and the game begins.

The top of the screen will show the current location (on the top line), a list of doors that you are able to go to (on the line directly underneath), and a list of people in the same room as you. To go to a different room, the `/go` command can be used. E.g. `/go Admin`. (Case sensitive.)

If the player is a crewmate, the screen will be divided vertically into two parts. The left half of the screen will contain the message box. The right half will list the tasks you have to complete. An empty box beside a task (`[  ]`) means it is not completed whereas a box with a hyphen (`[-]`) means it is completed. To do a task, go to the room specified. Then, complete it with `/do Task name`. E.g. if the task looks like `[  ] Swipe card @ Admin`, first navigate to `Admin`. Then, `/do Swipe card`, omitting the location. Upon completion, the box will fill in and will appear as `[-] Swipe card @ Admin`.


## Commands

* `/start`: Start the game (can only be run as admin)
* `/go LOCATION`: Go to the room `LOCATION`
* `/do TASK`: Attempt to complete the task `TASK`
* `/raw PACKET`: Send a raw packet to the server (shouldn't be used)
* `/tasks`: Refresh tasks list (useful if the tasks don't show or appear buggy)
* `/quit`: Quit the game

