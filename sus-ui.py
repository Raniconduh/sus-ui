import curses
import socket
from multiprocessing.dummy import Pool


pool = Pool(processes=1)
inpline = ""


def readall(s):
    s.settimeout(0.25)
    buf = ""
    try:
        while c := s.recv(1):
            try: buf += c.decode('utf-8')
            except UnicodeDecodeError: pass
    except socket.timeout:
        return buf

def readline(s):
    s.settimeout(None)
    buf = ''
    while c := s.recv(1):
        if c == b'\n':
            return buf
        try: buf += c.decode('utf-8')
        except UnicodeDecodeError: pass
    return buf


def get_serv_info(screen):
    screen.erase()
    screen.refresh()
    curses.echo()
    curses.curs_set(1)

    screen.addstr(1, 1, "Server IP/Hostname [localhost]: ")
    ip = screen.getstr(2, 1)

    screen.addstr(3, 1, "Server Port [1234]:")
    port = screen.getstr(4, 1)

    screen.addstr(5, 1, "Username:")
    uname = screen.getstr(6, 1)

    curses.noecho()
    curses.curs_set(0)

    ip = ip.decode('utf-8') if ip else 'localhost'
    port = int(port.decode('utf-8')) if port else 1234
    uname = uname

    return ip, port, uname


def getchcb(c):
    global inpline
    if c: inpline += chr(c)


def main(screen):
    global pool
    global inpline

    host, port, uname = get_serv_info(screen)
    screen.erase()
    screen.refresh()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))    

    s.send(uname + b'\n')

    row = 1
    column = 1

    chat_buf = []

    first_message = readall(s).split('\n')[:-2]
    for line in first_message:
        chat_buf.append(line)
        screen.addstr(row, column, line)
        row += 1
    screen.refresh()

    admin = False

    if first_message[1][-3:] == ' 0!':
        admin = True

    if admin:
        chat_buf.append("You are the admin")
        screen.addstr(row, column, "You are the admin")
        row += 1

    while True:
        #screen.erase()
        for line in readall(s).split('\n'):
            if line: chat_buf.append(line)

        for line in range(len(chat_buf)):
            if chat_buf[line]:
                screen.addstr(line + 1, column, chat_buf[line])

        max_height, max_width = screen.getmaxyx()

        pool.apply_async(screen.getch, callback=getchcb)
        if inpline and inpline[-1] == '\n':
            chat_buf.append(f'*you*: {inpline}')
            screen.addstr(row, column, chat_buf[-1])
            row += 1
            s.send(bytes(inpline, 'utf-8'))
            inpline = ""
            screen.erase()
        elif inpline and ord(inpline[-1]) == 127:
            inpline = inpline[:-2]

        screen.addstr(max_height - 2, 1, inpline+ ' ')

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


