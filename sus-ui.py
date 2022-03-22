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
    # client -> server
    COMMAND   = 6     # run command
    NAME      = 7     # set name
    LOCATION  = 8     # set location
    # client <-> server
    CLIENTS   = 9     # request clients
    CHAT      = 10    # send chat
    TASK      = 11    # do task


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

        self.clients = {}
        self.tasks = []
        self.doors = []
        self.location = ""
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

    def screen_getline(self): # read line of user input
        line = self.inp_box.getstr(0, 0)
        self.inp_box.erase()
        self.inp_box.refresh()
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
    
    def start_game(self):
        y, x = self.screen.getmaxyx()

        self.game_playing = True

        self.msg_box.erase()
        self.msg_box.refresh()

        self.msg_box = self.screen.subwin(y - 5, x // 2 - 1, 4, 1)
        self.msg_box.erase()
        self.msg_box.refresh()

        self.loc_box = self.screen.subwin(2, x - 1, 1, 1)
        self.loc_box.erase()
        self.loc_box.refresh()

        self.task_box = self.screen.subwin(y - 5, x // 2 - 1, 4, x // 2 + 1)
        self.task_box.erase()
        self.task_box.refresh()

        self.update_tasks()
        self.update_loc()
    
    def update_tasks(self):
        self.task_box.erase()
        self.task_box.addstr(0, 0, "Tasks:")
        for task in range(len(self.tasks)):
            done = ' '
            if self.tasks[task]["done"]: done = '-'
            desc = self.tasks[task]["description"]
            loc = self.tasks[task]["location"]
            self.task_box.addstr(task + 1, 0, f'[{done}] {desc} @ {loc}')
        self.task_box.refresh()
    
    # update location and doors
    def update_loc(self):
        self.loc_box.erase()
        self.loc_box.addstr(0, 0, self.location)
        c = 7
        self.loc_box.addstr(1, 0, "Doors: ")
        for door in self.doors:
            self.loc_box.addstr(1, c, f'{door} ')
            c += len(door) + 1
        self.loc_box.refresh()

    def command(self, com):
        lsplit = com.split(' ')
        # start game
        if com == "/start":
            com = {"type":JType.COMMAND,"arguments":{"name":"start_game"}}
            com = json.dumps(com)
            self.s.send(com.encode('utf-8'))
        # go to room
        elif lsplit[0] == "/go" and len(lsplit) > 1:
            pass
        # do task
        elif lsplit[0] == "/do" and len(lsplit) > 1:
            pass
        # quit game
        elif com == "/quit":
            self.s.close()
            return -1
        elif not self.game_playing:
            new_msg = {"type":JType.CHAT,"arguments":{"content":com}}
            new_msg = json.dumps(new_msg)
            self.s.send(new_msg.encode('utf-8'))
            self.message(f'<you>: {com}')

    def socket_handler(self):
        while line := self.sock_getline():
            line = json.loads(line)
            # server info - noop
            if line["type"] == JType.S_INFO: pass
            #client info - WIP
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
                    self.message(f'[{self.clients[p_id]} entered the room]')
                elif line["status"] == SCode.CLI_RLEAVE:
                    self.message(f'[{self.clients[p_id]} left the room]')
            # game status - WIP
            elif line["type"] == JType.GAME_STATUS:
                pass
            # room info
            elif line["type"] == JType.ROOM_INFO:
                self.location = line["arguments"]["name"]
                for door in line["arguments"]["doors"]:
                    self.doors.append(door)
                for client in line["arguments"]["clients"]:
                    if not client["alive"]:
                        # maybe show ID too
                        self.message(f'Body found: {self.clients[client["id"]]}')
                self.update_loc()
            # game state - might need to look at "state"
            elif line["type"] == JType.STATE:
                if "role" in line["arguments"]:
                    self.role = line["arguments"]["role"]
                    r = ""
                    if self.role == 0: r = "a crewmate"
                    elif self.role == 1: r = "an imposter"
                    self.message(f'You are {r}')
                if "state" in line["arguments"]:
                    if line["arguments"]["state"] == 2:
                        self.message("The game has started")
                        self.start_game()
            # tasks
            elif line["type"] == JType.TASKS:
                for task in line["arguments"]:
                    task["done"] = False
                    self.tasks.append(task)
            # command failed
            elif line["type"] == JType.COMMAND:
                c = line["arguments"]["name"]
                self.message(f'** Could not run command ({c}) **')
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
                    self.message("** Couldn't send chat **")
            # complete task - WIP
            elif line["type"] == JType.TASK:
                if line["status"] == SCode.GEN_OK:
                    for task in range(len(self.tasks)):
                        if self.tasks[task]["description"] == line["arguments"]["description"]:
                            self.tasks[task]["done"] = True
                            self.update_tasks()
                else:
                    self.message("** could not complete task **")
            else: self.message(f'** Unknown server response ({line}) **')

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
            elif c == ord('\b'):
                if not len(self.inpline): continue

                self.inpline = self.inpline[:1]
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
        handlers.message(f'Server verion \'{welcome["arguments"]["version"]}\'')
    # need to request current clients
    msg = json.dumps({"type":JType.CLIENTS})
    s.send(msg.encode('utf-8'))

    # start socket handler on separate thread
    t = Thread(target=handlers.socket_handler)
    t.setDaemon(True)
    t.start()
    try:
        # input handler can stay on main thread
        handlers.input_handler()
    except KeyboardInterrupt:
        return # exit


if __name__ == '__main__':
    curses.wrapper(main)

