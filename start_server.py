#!/srv/anaconda3/bin/python3.7

import server

if __name__ == '__main__':
    s = server.GameServer()
    s.start()
