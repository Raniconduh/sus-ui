# sus-ui

A client for [among-sus](https://github.com/Raniconduh/among-sus)


## Usage

After starting the client (`likely via ./sus-ui.py`), enter the IP (or hostname) and port of the server you wish to connect to. Pressing enter (without entering anything else) will use the default hostname (`localhost`) and port (`1234`). If the client is able to connect to a server with the given information, you will be prompted to enter a username.

Now, unless a game is already started on the server, you will be put into the lobby. At this point, the client is usable as a basic chat app. Once ready, the server admin can start the game with the `/start` command. If the game can be started, each client will be told whether they are an imposter or crewmate and the game begins.

The top left corner will look like so: `Location: Cafeteria  Doors: Admin`. `Location:` shows the current room you are in. `Doors:` shows the list of rooms that you can travel to. To travel to a different room, use the `/go` command. E.g. `/go Admin`.

The top right corner will be your list of tasks. An empty box beside a task (`[  ]`) means it is not completed whereas a box with a hyphen (`[-]`) means it is completed. To do a task, go to the room specified. Then, complete it with `/do Task name`. E.g. if the task looks like `[  ] Swipe card in Admin`, first navigate to `Admin`. Then, `/do Swipe card`, omitting the location. Upon completion, the box will fill in and will appear as `[-] Swipe card in Admin`.


## Commands

* `/start`: Start the game (can only be run as admin)
* `/location`: Refresh location information
* `/tasks`: Refresh current task information
* `/go LOCATION`: Go to the room `LOCATION`
* `/do TASK`: Attempt to complete the task `TASK`

