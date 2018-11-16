#!/srv/anaconda3/bin/python3.7

import socket
import logging
import projectconf as cf

logging.disable(logging.CRITICAL)
# logging.basicConfig(level=logging.DEBUG)


class GameClient:
    """
    Class for working with a remote GameServer.
    Usage:
        s = server.GameClient()
        s.start()
    """
    def __init__(self, host: str = cf.host, port: int = cf.port):
        self.host = host
        self.port = port
        self._socket = None
        self.player_name = ''
        self.player_id = ''

    def start(self):
        print('Welcome to %GAME%')
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self._socket:
                self._socket.connect((self.host, self.port))

                self._login()

                hello_msg = """
Choose from the following options:
1. Inventory
2. Shop
3. Game
4. Exit"""
                while True:
                    print(hello_msg)
                    try:
                        choice = int(input())
                        if choice == 1:
                            self._show_inventory()
                        elif choice == 2:
                            self._show_shop()
                        elif choice == 3:
                            self._game()
                        elif choice == 4:
                            self._socket.sendall(cf.encode({'logout': '1'}))
                            break

                    except ValueError:
                        pass
                print('Close connection')

        except ConnectionRefusedError:
            print("Server is not available. Try later or contact support")
        except BrokenPipeError:
            print("Broken pipe. Contact support")

    def _show_inventory(self):
        g = {'get': 'inventory', 'player_id': self.player_id}
        self._socket.sendall(cf.encode(g))

        response = cf.decode(self._socket.recv(cf._max_buffer))
        items = response['items']
        credits_ = response['credits']

        print('Inventory:')
        print('Credits: {}'.format(credits_))
        print('id  {:<25}{}'.format('name', 'price'))
        for idx, item in enumerate(items, 1):
            print('{:>2}. {:<25}{}'.format(idx, item['name'], item['price']))
        print(' 0. Exit')

        while True:
            try:
                n = int(input('Sell item: '))
                if not n:
                    break
                g = {'sell': items[n-1]['id'], 'player_id': self.player_id}
                self._socket.sendall(cf.encode(g))

                response = cf.decode(self._socket.recv(cf._max_buffer))
                if response['status'] == 'success':
                    print('Congratulations! You sold {}'.format(items[n-1]['name']))
                else:
                    print("Something went wrong")

                break

            except (ValueError, IndexError):
                print("Incorrect input")
                continue

    def _show_shop(self):
        g = {'get': 'items', 'player_id': self.player_id}
        self._socket.sendall(cf.encode(g))

        response = cf.decode(self._socket.recv(cf._max_buffer))
        items = response['items']

        g = {'get': 'credits', 'player_id': self.player_id}
        self._socket.sendall(cf.encode(g))

        response = cf.decode(self._socket.recv(cf._max_buffer))
        cr = response['credits']

        print('Shop:')
        print('Your credits: {}'.format(cr))

        print('id  {:<25}{}'.format('name', 'price'))
        for idx, item in enumerate(items, 1):
            print('{:>2}. {:<25}{}'.format(idx, item['name'], item['price']))
        print(' 0. Exit')

        while True:
            try:
                n = int(input('Buy item: '))
                if not n:
                    break
                g = {'buy': items[n-1]['id'], 'player_id': self.player_id}
                self._socket.sendall(cf.encode(g))

                response = cf.decode(self._socket.recv(cf._max_buffer))
                if response['status'] == 'success':
                    print('Congratulations! You bought {}'.format(items[n-1]['name']))
                else:
                    print("Something went wrong")

                break

            except (ValueError, IndexError):
                print("Incorrect input")
                continue

    def _login(self):
        while True:
            login = input('Your login: ')
            self._socket.sendall(cf.encode({'login': login}))

            login_response = cf.decode(self._socket.recv(cf._max_buffer))
            logging.debug('login_response: {}'.format(login_response))

            if not isinstance(login_response, dict):
                logging.error('login_response is not dict: {}'.format(login_response))
                print('Login error. Please try again')
                continue

            n = login_response.get('nickname', '')
            if n:
                self.player_name = n
                self.player_id = login_response.get('id', '')
                print('Hello {}!'.format(self.player_name))
                break

    def _game(self):
        print("Let's play")
        while True:
            try:
                g = {'get': 'credits', 'player_id': self.player_id}
                self._socket.sendall(cf.encode(g))

                response = cf.decode(self._socket.recv(cf._max_buffer))
                cr = response['credits']

                bet = int(input('Your bet (from 1 to {}, 0 - exit): '.format(cr)))

                if bet == 0:
                    break

                g = {'game': bet, 'player_id': self.player_id}
                self._socket.sendall(cf.encode(g))

                response = cf.decode(self._socket.recv(cf._max_buffer))
                if response['status'] == 'success':
                    print('Congratulations! You win {}'.format(bet))
                else:
                    print("Don't be upset. Try again")

            except (ValueError, IndexError):
                print("Incorrect input")
                continue
