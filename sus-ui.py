#!/usr/bin/env python3

import curses
import socket
import json


# read all data in socket
def readall(s):
    s.settimeout(0.25)
    buf = ""
    try:
        while c := s.recv(1):
            try: buf += c.decode('utf-8')
            except UnicodeDecodeError: pass
    except socket.timeout:
        return buf

# read single line in socket
def readline(s):
    s.settimeout(0.005)
    buf = ''
    try:
        while c := s.recv(1):
            if c == b'\n':
                return buf
            try: buf += c.decode('utf-8')
            except UnicodeDecodeError: pass
    except socket.timeout:
        return None
    screen.erase()
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

    max_height, max_width = screen.getmaxyx()

    # set getch() to non-blocking
    screen.timeout(0)
    
    inpline = ""

    screen.erase()

    # chat
    while True:
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
            else:
                chat_buf.append(f'**Unknown server response** [{line["type"]}]')

        # handle inputs
        if (c := screen.getch()) != -1:
            if c == ord('\n'):
                new_msg = {"type":"message", "arguments":{"message":inpline}}
                new_msg = json.dumps(new_msg)

                s.send(new_msg.encode('utf-8'))

                chat_buf.append(f'[you]: {inpline}')
                inpline = ""

                clear_flag = True
            elif c == ord('\b') or c == 127:
                inpline = inpline[:-1]
                mov_curs_flag = True
            else:
                inpline += chr(c)

        if len(chat_buf) == max_height - 3:
            chat_buf = chat_buf[1:]
            clear_flag = True

        if clear_flag:
            screen.erase()

        # print chat buffer to screen
        for line in range(len(chat_buf)):
            screen.addstr(line + 1, col, chat_buf[line])

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


