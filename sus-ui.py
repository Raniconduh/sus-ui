#!/usr/bin/env python3

import curses
import socket
import json
from threading import Thread


class JType():
    # server -> client
    S_INFO    = 0     # server
    C_INFO    = 1     # client
    GAME_STATUS = 2
    ROOM_INFO = 3
    STATE     = 4     # client state
    TASKS     = 5     # tasks list
    DATA      = 6
    # client -> server
    COMMAND   = 7     # run command
    NAME      = 8     # set name
    LOCATION  = 9     # set location
    KILL      = 10
    # client <-> server
    CLIENTS   = 11     # request clients
    CHAT      = 12    # send chat
    TASK      = 13    # do task


class SCode():
    # generic
    GEN_OK     = 0    # OK response
    GEN_INVAL  = 1    # invalid packet
    GEN_AGAIN  = 2    # packet resent
    # name
    NAME_WLEN  = 3    # name bad length
    # game
    GAME_NOTIN = 4    # client not playing
    GAME_WROLE = 5    # wrong role
    GAME_WLOC  = 6    # wrong location
    #client
    CLI_SJOIN   = 0   # server join
    CLI_SLEAVE  = 1   # server leave
    CLI_RENTER  = 2   # room enter
    CLI_RLEAVE  = 3   # room leave
    CLI_VOTE    = 4   # voted out
    # game status
    GSTAT_FULL    = 0 # game full
    GSTAT_RUNNING = 1 # game started
    GSTAT_IMPWIN  = 2 # imposter victory
    GSTAT_CREWWIN = 3 # crew victory

# read single line in socket
def readline(s):
    buf = ''
    while c := s.recv(1):
        if c == b'\n':
            return buf
        try: buf += c.decode('utf-8')
        except UnicodeDecodeError: pass
    return buf


def _get_server_info(screen):
    screen.erase()
    screen.refresh()
    curses.echo()
    curses.curs_set(1)

    screen.addstr(1, 1, "Server IP/Hostname [localhost]: ")
    ip = screen.getstr(2, 1)

    screen.addstr(3, 1, "Server Port [1234]:")
    port = screen.getstr(4, 1)
    
    curses.noecho()
    curses.curs_set(0)

    try: ip = ip.decode('utf-8') if ip else 'localhost'
    except UnicodeDecodeError: return False, False

    try: port = int(port.decode('utf-8')) if port else 1234
    except Exception: return False, False

    return ip, port


# get server host and port
def get_server_info(screen):
    host, port = _get_server_info(screen)
    while not host or not port:
        screen.erase()
        screen.addstr(1, 1, 'Invalid host or port entered')
        screen.refresh()
        curses.napms(1000)
        host, port = _get_server_info(screen)

    return host, port


def _connect_to_socket(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try: s.connect((host, port))
    except Exception: return False

    return s


# connect to the socket
def connect_to_socket(screen, host, port):
    s = _connect_to_socket(host, port)
    while not s:
        screen.erase()
        screen.addstr(1, 1, "Could not connect to socket")
        screen.refresh()
        curses.napms(1000)
        host, port = get_server_info(screen)
        s = _connect_to_socket(host, port)
    
    return s

 
def _get_uname(screen):
    screen.erase()
    curses.echo()
    curses.curs_set(1)

    screen.addstr(1, 1, "Enter your username:")
    uname = screen.getstr(2, 1)

    curses.noecho()
    curses.curs_set(1)

    if not uname:
        return False
    
    try: uname = uname.decode('utf-8')
    except Exception: return False

    return uname


# get username
def get_uname(screen):
    uname = _get_uname(screen)
    while not uname:
        screen.erase()
        screen.addstr(1, 1, "Invalid username")
        screen.refresh()
        curses.napms(1000)
        uname = _get_uname(screen)
    return uname


class BlockHandler():
    def __init__(self, sock, screen):
        self.s = sock
        self.screen = screen

        # initialize empty variables
        self.loc_box = None
        self.task_box = None

        # relate ID (index) to task and location
        self.local_tasks = [] # [{"desc": "description", "loc": 0}, ...]
        self.local_locs  = [] # ["Cafeteria", ...]
        self.local_doors = [] # [[0, 1, 2], ...]

        self.clients = {}
        self.room_clients = []
        self.tasks = []
        self.location = 0
        self.role = -1

        self.inpline = ""
        self.msg_buf = []

        self.game_playing = False

        y, x = self.screen.getmaxyx()

        self.msg_box = self.screen.subwin(y - 2, x - 1, 1, 1)
        self.inp_box = self.screen.subwin(1, x - 1, y - 2, 1)

        self.msg_box.erase()
        self.msg_box.refresh()

        self.inp_box.erase()
        self.inp_box.refresh()

    def sock_getline(self): # read line from socket
        line = b''
        while (c := self.s.recv(1)) != b'\n': line += c
        try: return line.decode('utf-8')
        except Exception: return None

    def message(self, s): # print to message buffer
        y, x = self.screen.getmaxyx()

        self.msg_buf.append(s)
        y, x = self.msg_box.getmaxyx()
        if len(self.msg_buf) == y:
            self.msg_buf = self.msg_buf[1:]
        self.msg_box.erase()
        for line in range(len(self.msg_buf)):
            self.msg_box.addstr(line, 1, self.msg_buf[line])
        self.msg_box.refresh()

        # move cursor to previous pos
        self.screen.move(y, 1 + len(self.inpline))
        self.screen.refresh()
        # redraw input line
        self.inp_box.addstr(0, 0, self.inpline)
        self.inp_box.refresh()

    def serr(self, s):
        self.message(f"** {s} **")

    # takes pure dict
    def send_pack(self, packet, raw=None):
        if packet and not raw:
            try: packet = json.dumps(packet)
            except Exception: return 1
        elif raw:
            packet = raw
        try: self.s.send(packet.encode('utf-8'))
        except UnicodeEncodeError: return 2
    
    def start_game(self):
        y, x = self.screen.getmaxyx()

        self.game_playing = True

        self.msg_box.erase()
        self.msg_box.refresh()

        self.loc_box = self.screen.subwin(2, x - 1, 1, 1)
        self.loc_box.erase()
        self.loc_box.refresh()

        self.client_box = self.screen.subwin(1, x - 1, 3, 1)
        self.client_box.erase()
        self.client_box.refresh()

        if self.role == 0: # crewmate
            self.msg_box = self.screen.subwin(y - 6, x // 2 - 1, 5, 1)

            self.task_box = self.screen.subwin(y - 6, x // 2 - 1, 5, x // 2 + 1)
            self.task_box.erase()
            self.task_box.refresh()
        elif self.role == 1: # imposter
            self.msg_box = self.screen.subwin(y - 6, x - 1, 5, 1)

        self.msg_box.erase()
        self.msg_box.refresh()

        self.update_tasks()
        self.update_loc()

        self.message("The game has started")
    
    def update_tasks(self):
        if self.role == 1: return
        self.task_box.erase()
        self.task_box.addstr(0, 0, "Tasks:")
        for task in range(len(self.tasks)):
            done = ' '
            if self.tasks[task]["done"]: done = '-'
            desc = self.local_tasks[self.tasks[task]["id"]]["desc"]
            loc = self.local_locs[self.local_tasks[self.tasks[task]["id"]]["loc"]]
            self.task_box.addstr(task + 1, 0, f'[{done}] {desc} @ {loc}')
        self.task_box.refresh()
    
    # update location and doors
    def update_loc(self):
        self.loc_box.erase()
        self.loc_box.addstr(0, 0, self.local_locs[self.location])
        c = 7
        self.loc_box.addstr(1, 0, "Doors: ")
        for door in self.local_doors[self.location]:
            self.loc_box.addstr(1, c, f'{self.local_locs[door]}  ')
            c += len(self.local_locs[door]) + 2 # leave 2 spaces between each door
        self.loc_box.refresh()

    def update_ir_clients(self):
        self.client_box.erase()
        c = 6
        self.client_box.addstr(0, 0, "Room: ")
        for client in self.room_clients:
            self.client_box.addstr(0, c, self.clients[client])
            c += len(self.clients[client]) + 2
        self.client_box.refresh()

    def command(self, com):
        lsplit = com.split(' ')
        # start game
        if com == "/start":
            self.send_pack({"type":JType.COMMAND,"arguments":{"name":"start_game"}})
        # go to room
        elif lsplit[0] == "/go" and len(lsplit) > 1:
            loc = ' '.join(lsplit[1:])
            if loc in self.local_locs:
                loc = self.local_locs.index(loc)
                self.send_pack({"type":JType.LOCATION,"arguments":{"id":loc}})
            else:
                self.serr("Bad location")
        # do task
        elif lsplit[0] == "/do" and len(lsplit) > 1:
            desc = ' '.join(lsplit[1:])
            attempt = False
            for task in range(len(self.local_tasks)):
                if self.local_tasks[task]["desc"] == desc and self.local_tasks[task]["loc"] == self.location:
                    attempt = True
                    self.send_pack({"type":JType.TASK,"arguments":{"id":task}})
            if not attempt:
                self.serr("Invalid task")
        # kill player
        elif lsplit[0] == "/kill":
            name = ' '.join(lsplit[1:])
            attempt = False
            for k, v in self.clients.items():
                if v == name:
                    attempt = True
                    self.send_pack({"type":JType.KILL,"arguments":{"id":k}})
            if not attempt:
                self.serr("Invalid player")
        # raw command
        elif lsplit[0] == "/raw":
            com = ' '.join(lsplit[1:])
            self.send_pack(None, raw=com)
        # refresh tasks
        elif com == "/tasks":
            self.update_tasks()
        # quit game
        elif com == "/quit":
            self.s.close()
            return -1
        elif not self.game_playing:
            self.send_pack({"type":JType.CHAT,"arguments":{"content":com}})
            self.message(f'<you>: {com}')

    def socket_handler(self):
        while line := self.sock_getline():
            line = json.loads(line)
            # server info - noop
            if line["type"] == JType.S_INFO: pass
            # client info - WIP
            elif line["type"] == JType.C_INFO:
                if "name" in line["arguments"]: player = line["arguments"]["name"]
                else: player = None
                p_id = line["arguments"]["id"]
                if line["status"] == SCode.CLI_SJOIN:
                    self.clients[p_id] = player
                    self.message(f'[{player} joined the game]')
                elif line["status"] == SCode.CLI_SLEAVE:
                    del self.clients[p_id]
                    self.message(f'[{player} left the game]')
                elif line["status"] == SCode.CLI_RENTER:
                    self.room_clients.append(p_id)
                    self.message(f'[{self.clients[p_id]} entered the room]')
                    self.update_ir_clients()
                elif line["status"] == SCode.CLI_RLEAVE:
                    del self.room_clients[self.room_clients.index(p_id)]
                    self.message(f'[{self.clients[p_id]} left the room]')
                    self.update_ir_clients()
            # game status
            elif line["type"] == JType.GAME_STATUS:
                if "arguments" in line and "winner" in line["arguments"]:
                    if line["arguments"]["winner"] == 0:
                        self.message("Crewmates Win!")
                    elif line["arguments"]["winner"] == 1:
                        self.message("Imposters Win!")
            # room info
            elif line["type"] == JType.ROOM_INFO:
                self.location = line["arguments"]["id"]
                self.room_clients = []
                for client in line["arguments"]["clients"]:
                    if not client["alive"]:
                        self.message(f'Body found: {self.clients[client["id"]]}')
                    else:
                        self.room_clients.append(client["id"])
                self.update_ir_clients()
                self.update_loc()
            # game state
            elif line["type"] == JType.STATE:
                if "role" in line["arguments"]:
                    self.role = line["arguments"]["role"]
                    r = ""
                    if self.role == 0: r = "a crewmate"
                    elif self.role == 1: r = "an imposter"
                    self.message(f'You are {r}')
                if "stage" in line["arguments"]:
                    if line["arguments"]["stage"] == 2:
                        self.start_game()
            # tasks
            elif line["type"] == JType.TASKS: 
                self.tasks = []
                for t in line["arguments"]:
                    task = {"id": t, "done": False}
                    self.tasks.append(task)
                self.update_tasks()
            # initial game data
            elif line["type"] == JType.DATA:
                self.local_tasks = [t for t in line["arguments"]["tasks"]]
                self.local_doors = [d["doors"] for d in line["arguments"]["locations"]]
                self.local_locs  = [n["name"] for n in line["arguments"]["locations"]]
            # command failed
            elif line["type"] == JType.COMMAND:
                if line["status"] != SCode.GEN_OK:
                    self.serr("Could not run command")
            # list clients
            elif line["type"] == JType.CLIENTS:
                for client in line["arguments"]:
                    self.clients[client["id"]] = client["name"]
            # chat
            elif line["type"] == JType.CHAT:
                if "arguments" in line:
                    name = self.clients[line["arguments"]["id"]]
                    message = line["arguments"]["content"]
                    self.message(f'[{name}]: {message}')
                elif "status" in line and line["status"] != 0:
                    self.serr("Could not send chat")
            # location
            elif line["type"] == JType.LOCATION:
                if line["status"] == SCode.GAME_WLOC:
                    self.serr("Wrong location")
                elif line["status"] != SCode.GEN_OK:
                    self.serr("Bad location")
            # complete task
            elif line["type"] == JType.TASK:
                if line["status"] == SCode.GEN_OK:
                    for task in range(len(self.tasks)):
                        if self.tasks[task]["id"] == line["arguments"]["id"]:
                            self.tasks[task]["done"] = True
                            self.update_tasks()
                else:
                    self.serr("Could not complete task")
            else: self.serr(f'Unknown server response ({line})')

    def input_handler(self):
        y, x = self.screen.getmaxyx()
        self.screen.move(y - 2, 1)

        while True:
            c = self.inp_box.getch()

            if not c or c == -1: continue

            if c == ord('\n'):
                # exit if necessary: returns -1
                if self.command(self.inpline) == -1: return
                self.inpline = ''
                self.inp_box.erase()

                self.inp_box.refresh()
            elif c == ord('\b') or c == 127:
                if not len(self.inpline): continue
                if len(self.inpline) == 1:
                    self.inpline = ""

                self.inpline = self.inpline[:-1]
                self.inp_box.erase()
                self.inp_box.addstr(0, 0, self.inpline)

                self.inp_box.refresh()
            elif c != ord('\033'): # not ESC
                self.inpline += chr(c)

                self.inp_box.erase()
                self.inp_box.addstr(0, 0, self.inpline)
                self.inp_box.refresh()


def main(screen):
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()

    screen.clear()
    screen.refresh()

    host, port = get_server_info(screen)
    s = connect_to_socket(screen, host, port)

    # to be used later
    welcome = readline(s)
    if welcome: welcome = json.loads(welcome)

    name = get_uname(screen)

    nd = {"type":JType.NAME, "arguments":{"name":name}}
    nd = json.dumps(nd)

    s.send(nd.encode('utf-8'))
    
    name_response = readline(s)
    while not name_response:
        name_response = readline(s)
    name_response = json.loads(name_response)

    # invalid name
    while name_response["status"] != SCode.GEN_OK:
        err = ""
        if name_response["status"] == SCode.NAME_WLEN:
            err = "Name too long or too short"
        else:
            err = "Bad name input"
        screen.erase()
        screen.addstr(1, 1, err)
        screen.refresh()
        curses.napms(1000)
        
        name = get_uname(screen)
        nd = json.dumps({"type":JType.NAME, "arguments":{"name":name}})
        s.send(nd.encode('utf-8'))
        
        name_response = readline(s)
        while not name_response:
            name_response = readline(s)
        name_response = json.loads(name_response)

    screen.erase()

    handlers = BlockHandler(s, screen)

    # welcome!
    if welcome:
        handlers.message(f'Server version \'{welcome["arguments"]["version"]}\'')
    # need to request current clients
    msg = json.dumps({"type":JType.CLIENTS})
    s.send(msg.encode('utf-8'))

    # start socket handler on separate thread
    t = Thread(target=handlers.socket_handler)
    t.daemon = True
    t.start()
    try:
        # input handler can stay on main thread
        handlers.input_handler()
    except KeyboardInterrupt:
        return # exit


if __name__ == '__main__':
    curses.wrapper(main)

