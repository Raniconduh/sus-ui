#!/usr/bin/env python3

import curses
import socket
import json


sock_closed = False


# read all data in socket
def readall(s):
    buf = ""
    try:
        while c := s.recv(1):
            try: buf += c.decode('utf-8')
            except UnicodeDecodeError: pass
    except BlockingIOError:
        pass
    return buf

# read single line in socket
def readline(s):
    global sock_closed
    buf = ''
    try:
        while c := s.recv(1):
            if c == b'\n':
                return buf
            try: buf += c.decode('utf-8')
            except UnicodeDecodeError: pass
    except BlockingIOError:
        return None
    if not buf:
        sock_closed = True
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


def main(screen):
    host, port = get_server_info(screen)
    s = connect_to_socket(screen, host, port)
    s.setblocking(False)

    name = get_uname(screen)

    welcome = readall(s)
    welcome = json.loads(welcome)

    nd = {"type":"name", "arguments":{"name": name}}
    nd = json.dumps(nd)

    s.send(nd.encode('utf-8'))

    name_response = readall(s)
    name_response = json.loads(name_response)

    name_stauses = {
            0: "Name Too Short",
            1: "Name Too Long",
            2: "Invalid Name",
            3: "Name Taken"
    }

    # invalid name
    while name_response["type"] != "greeting":
        screen.erase()
        screen.addstr(1, 1, name_stauses[name_response["status"]])
        screen.refresh()
        curses.napms(1000)
        
        name = get_uname(screen)
        nd = json.dumps({"type":"name", "arguments":{"name":name}})
        s.send(nd.encode('utf-8'))

        name_response = json.loads(readall(s))

    chat_buf = []

    row = 1
    col = 1

    # set getch() to non-blocking
    screen.timeout(0)

    inpline = ""
    screen.erase()
    read_next = 0
    game_play = False
    CREW = (0)
    IMP = (1)
    GHOST = (2)
    player_types = ("crewmate", "imposter", "ghost")
    player_type = None
    location = None
    doors = []
    tasks = []

    global sock_closed

    # chat
    while True:
        max_height, max_width = screen.getmaxyx()
        mov_curs_flag = False
        clear_flag = False

        if line := readline(s):
            line = json.loads(line)
            if line["type"] == "chat":
                sender = line["arguments"]["player"]
                msg = line["arguments"]["message"]
                chat_buf.append(f'[{sender}]: {msg}')
            elif line["type"] == "join":
                player = line["arguments"]["player"]
                chat_buf.append(f'[{player} joined the lobby]')
            elif line["type"] == "leave":
                player = line["arguments"]["player"]
                chat_buf.append(f'[{player} left the lobby]')
            elif line["type"] == "game_status":
                if line["status"] == 0:
                    game_play = True
                    new_com = {"type":"location"}
                    s.send(json.dumps(new_com).encode('utf-8'))
                    new_com = {"type":"tasks"}
                    s.send(json.dumps(new_com).encode('utf-8'))
            elif line["type"] == "player_type":
                player_type = int(line["status"])
                tmp_type = player_types[player_type]
                chat_buf.append(f'[You are {"an" if player_type == 1 else "a"} {tmp_type}]')
            elif line["type"] == "location" and line["status"] == 1:
                location = line["arguments"]["name"]
                doors = [door for door in line["arguments"]["doors"]]
            elif line["type"] == "set_location":
                pass
            elif line["type"] == "tasks":
                tasks = [task for task in line["arguments"]]
            elif line["type"] == "do_task":
                chat_buf.append('**Did task**')
            else:
                chat_buf.append(f'**Unknown server response** [{line["type"]}]')

        if sock_closed:
            return

        # handle inputs
        if (c := screen.getch()) != -1 and not read_next:
            if c == ord('\n') and inpline.strip():
                isplit = inpline.split(' ')
                if inpline == '/start':
                    new_com = {"type":"command","arguments":{"command":"start","arguments":[]}}
                    s.send(json.dumps(new_com).encode('utf-8'))
                elif inpline == '/location':
                    new_com = {"type":"location"}
                    s.send(json.dumps(new_com).encode('utf-8'))
                elif isplit[0] == '/go' and len(isplit) == 2:
                    new_com = {"type":"set_location","arguments":{"name":isplit[1]}}
                    s.send(json.dumps(new_com).encode('utf-8'))
                    
                    new_com = {"type":"location"}
                    s.send(json.dumps(new_com).encode('utf-8'))
                elif inpline == "/tasks":
                    new_com = {"type": "tasks"}
                    s.send(json.dumps(new_com).encode('utf-8'))
                elif isplit[0] == '/do' and len(isplit) > 1:
                    new_com = {"type":"do_task","arguments":{"name":' '.join(isplit[1:]),"location":location}}
                    s.send(json.dumps(new_com).encode('utf-8'))
                    new_com = {"type":"tasks"}
                    s.send(json.dumps(new_com).encode('utf-8'))
                elif not game_play:
                    new_msg = {"type":"message","arguments":{"message":inpline}}
                    new_msg = json.dumps(new_msg)
                    s.send(new_msg.encode('utf-8'))

                    chat_buf.append(f'[you]: {inpline}')

                inpline = ""
                clear_flag = True
            elif c == ord('\n') and not inpline.strip():
                y, x = screen.getyx()
                screen.move(y - 1, x)
            elif c == ord('\b') or c == 127: # DEL
                inpline = inpline[:-1]
                mov_curs_flag = True
            elif c == 27: # ESC
                read_next = 3
            else:
                inpline += chr(c)

        if read_next: read_next -= 1

        if len(chat_buf) == max_height - 3:
            chat_buf = chat_buf[1:]
            clear_flag = True

        if clear_flag:
            screen.erase()

        # print chat buffer to screen
        for line in range(len(chat_buf)):
            screen.addstr(line + 3, col, chat_buf[line])

        # print location and doors to top of screen
        if location and doors:
            screen.addstr(1, 1, f'Location: {location}  Doors: {" ".join(doors)}')
        else:
            screen.addstr(1, 1, f'Lobby')

        # display tasks
        if tasks:
            screen.addstr(1, max_width - 45, "Tasks:")
            for task in range(len(tasks)):
                done = '-' if tasks[task]["done"] else ' '
                taskd = tasks[task]["description"]
                loc = tasks[task]["location"]
                screen.addstr(task + 2, max_width - 45, f'[{done}] {taskd} in {loc}')
        elif game_play:
            new_com = {"type":"tasks"}
            s.send(json.dumps(new_com).encode('utf-8'))

        if mov_curs_flag:
            screen.addstr(max_height - 2, col, inpline + ' ')
            y, x = screen.getyx()
            screen.move(y, x - 1)
        else:
            screen.addstr(max_height - 2, col, inpline)

        screen.refresh()


if __name__ == '__main__':
    screen = curses.initscr()
    curses.curs_set(0)
    curses.noecho()
    curses.cbreak()
    
    screen.clear()
    screen.refresh()

    try:
        main(screen)
    except KeyboardInterrupt:
        pass

    curses.nocbreak()
    curses.echo()
    curses.curs_set(1)
    curses.endwin()

    if sock_closed:
        print("Connection closed unexpectedly")
        quit(1)

