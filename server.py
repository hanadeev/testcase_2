#!/srv/anaconda3/bin/python3.7

import asyncio
import sqlite3
import json
import logging
import random
import projectconf as cf

logging.disable(logging.CRITICAL)
# logging.basicConfig(level=logging.DEBUG)


class DataBase:
    """ Layer for working with a database """

    def __init__(self, base_name: str = cf.base_name):
        self.conn = sqlite3.connect(base_name)  # Connection
        logging.debug("Base client: {}".format(self.conn))

        def dict_factory(cursor, row) -> dict:
            """ Func for row_factory """
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.conn.row_factory = dict_factory
        self.cursor = self.conn.cursor()  # Cursor

    def close(self):
        self.conn.commit()
        self.conn.close()

    def create_items(self):
        """ re-create table items """
        items_prop = [list(i.values()) for i in cf.items]

        self.cursor.execute("DELETE FROM items")
        self.cursor.executemany("INSERT INTO items (name, price) "
                                "VALUES (?, ?)", items_prop)

    def create_tables(self):
        """ re-create tables """
        # self.cursor.execute("DROP TABLE player_items")
        # self.cursor.execute("DROP TABLE players")
        # self.cursor.execute("DROP TABLE items")

        self.cursor.execute("CREATE TABLE players ("
                            "id integer primary key,"
                            "nickname varchar(20) unique,"
                            "credits integer not null);"
                            "")
        self.cursor.execute("CREATE TABLE items ("
                            "id integer primary key,"
                            "name varchar(100) not null,"
                            "price integer not null,"
                            "description text);"
                            "")
        self.cursor.execute("CREATE TABLE player_items ("
                            "trans_id integer primary key,"
                            "player_id integer not null,"
                            "item_id integer not null,"
                            "foreign key (player_id) references players(id),"
                            "foreign key (item_id)  references items(id));"
                            "")

    def get_player(self, nickname: str = '', id_: int = 0) -> dict:
        if id_:
            self.cursor.execute("SELECT * FROM players WHERE id=:id",
                                {'id': id_})
        elif nickname:
            self.cursor.execute('SELECT * FROM players WHERE nickname=:nickname',
                                {'nickname': nickname})
        else:
            return {}

        result = self.cursor.fetchone()
        if result:
            return result
        else:
            return {}

    def create_player(self, nickname: str, credits_: int = cf.default_credits) -> dict:
        try:
            self.cursor.execute("INSERT INTO players (nickname, credits) "
                                "VALUES (:nickname, :credits)",
                                {'nickname': nickname, 'credits': credits_})
        except sqlite3.DatabaseError as e:
            logging.error("create_player error: {}".format(e.args))
            return {}

        self.conn.commit()
        return self.get_player(nickname)

    def buy_item(self, player_id_: int, item_id_: int) -> dict:
        try:
            player = self.get_player(id_=player_id_)
            cost = self.get_cost(item_id_)
            balance = player.get('credits', 0) - cost.get('price', 99999)

            if balance < 0:
                return {'status': 'failed'}

            self.cursor.execute("INSERT INTO player_items (player_id, item_id) "
                                "VALUES (:player_id_, :item_id_)",
                                {'player_id_': player_id_, 'item_id_': item_id_})

            self.set_balance(player_id_, balance)

        except sqlite3.DatabaseError as e:
            logging.error("buy_item error: {}".format(e.args))
            return {'status': 'failed'}

        self.conn.commit()
        return {'status': 'success'}

    def sell_item(self, player_id_: int, item_id_: int) -> dict:
        try:
            player = self.get_player(id_=player_id_)
            cost = self.get_cost(item_id_)
            balance = player.get('credits', 0) + cost.get('price', 0)

            if balance < 0:
                return {'status': 'failed'}

            self.cursor.execute("SELECT * FROM player_items "
                                "WHERE player_id=:player_id_ and item_id=:item_id_",
                                {'player_id_': player_id_, 'item_id_': item_id_})

            if not self.cursor.fetchone():
                return {'status': 'failed'}

            self.cursor.execute("DELETE FROM player_items "
                                "WHERE player_id=:player_id_ and item_id=:item_id_",
                                {'player_id_': player_id_, 'item_id_': item_id_})

            self.set_balance(player_id_, balance)

        except sqlite3.DatabaseError as e:
            logging.error("sell_item error: {}".format(e.args))
            return {'status': 'failed'}

        self.conn.commit()
        return {'status': 'success'}

    def get_cost(self, item_id_: int) -> dict:
        self.cursor.execute("SELECT price FROM items WHERE id=:id",
                            {'id': item_id_})
        result = self.cursor.fetchone()
        if result:
            return result
        else:
            return {}

    def get_items(self, player_id_: int) -> dict:
        self.cursor.execute("""SELECT * FROM items WHERE id NOT IN
                                    (SELECT item_id FROM player_items
                                    WHERE player_id=:player_id_)""", {'player_id_': player_id_})
        result = self.cursor.fetchall()
        if result:
            return {'items': result}
        else:
            return {}

    def get_player_items(self, player_id_: int) -> dict:
        self.cursor.execute("""SELECT * FROM items WHERE id IN
                            (SELECT item_id FROM player_items
                            WHERE player_id=:player_id_)""", {'player_id_': player_id_})
        result = self.cursor.fetchall()
        credits_ = self.get_player(id_=player_id_)['credits']
        return {'items': result, 'credits': credits_}

    def get_credits(self, id_: int) -> dict:
        credits_ = self.get_player(id_=id_)['credits']
        return {'credits': credits_}

    def set_balance(self, player_id_: int, balance: int) -> dict:
        try:
            self.cursor.execute("UPDATE players SET credits=:balance "
                                "WHERE id=:player_id_",
                                {'balance': balance, 'player_id_': player_id_})
        except sqlite3.DatabaseError as e:
            logging.error("set_balance error: {}".format(e.args))
            return {}

        self.conn.commit()


class GameServer:
    """Class for creation and running TCP Socket Server, and for connection to database
    usage:
        s = server.GameServer()
        s.start()
    """

    def __init__(self, host: str = cf.host, port: int = cf.port):
        self.host = host
        self.port = port
        self.db = DataBase()

    def start(self):
        loop = asyncio.get_event_loop()
        coro = asyncio.start_server(self.handle_request, self.host, self.port, loop=loop)
        try:
            server = loop.run_until_complete(coro)
        except OSError as e:
            print('Error. Address already in use ({}:{})'.format(self.host, self.port))
            logging.error("OSError: {}".format(e.args))
            return
        print('Start server on {}'.format(server.sockets[0].getsockname()))
        # Serve requests until Ctrl+C is pressed
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print('KeyboardInterrupt. Exit')
            pass

        # TODO При одновременном подключении нескольких клиентов остальные на остановку сервера никак не отреагировали.
        # Но при попытке отправки какого-либо запроса клиенты падали на необработанном исключении.
        #
        # Решение: у сервера должен быть список (например, в виде таблицы БД) залогинившихся в текущий момент
        # пользователей (в данном случае можно пройтись по запущенным сопрограммам).
        # При остановке сервера он должен рассылать этому списку уведомления о своей остановке.
        # Ну и соответственно, сделать обработку этого уведомления на клиенте.

        # Close the server
        self.db.close()
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

    async def handle_request(self, reader, writer):
        """
        API
        1. request: {'login': nickname}
            answer: dict with player's properties
        2. request: {'get': items, 'player_id': id}
            answer: dict with items which can be bought
        3. request: {'get': inventory, 'player_id': id}
            answer: dict with user's items
        4. request: {'buy': item_id, 'player_id': id}
            answer: {'status': 'failed' | 'success'}
        5. request: {'sell': item_id, 'player_id': id}
            answer: {'status': 'failed' | 'success'}
        6. request: {'game': bet, 'player_id': id}
            answer: {'status': 'failed' | 'success'}
        7. request: {'logout': nickname}
            No answer, just close connection
        """
        try:
            addr = writer.get_extra_info('peername')
            while True:
                # TODO При обработке запросов от клиента на сервере нет проверки на некорректные аргументы – никак
                # не обрабатываются случаи, если данные по указанному player_id отсутствуют.
                #
                # Решение: проверка валидности данных на стороне сервере обязательна. Проверки на стороне
                # клиента нужны в основном для того, чтобы не нагружать сервер заведомо неверными запросами. Поэтому
                # обычно проверки на стороне клиента - поверхностные, на общую корректность. Все остальное на сервере:
                # можно ли что-то сделать, есть ли такой пользователь, есть ли у него права на это действие и т.д.
                # Правильным решением будет использование что-то вроде
                # if not self.valid(request): data = {'status': 'failed'}

                data = None
                request_b = await reader.read(cf._max_buffer)
                request = cf.decode(request_b)
                logging.debug('Server received from {}: {}'.format(addr, request))
                keys_ = request.keys()

                if 'login' in keys_:
                    data = self.login(request['login'])
                    if not data:
                        data = {'status': 'failed'}

                elif 'get' in keys_:
                    if request['get'] == 'items':
                        data = self.get_items(request['player_id'])
                    elif request['get'] == 'inventory':
                        data = self.get_player_items(request['player_id'])
                    elif request['get'] == 'credits':
                        data = self.get_credits(request['player_id'])

                elif 'buy' in keys_:
                    data = self.buy_item(request['player_id'], request['buy'])

                elif 'sell' in keys_:
                    data = self.sell_item(request['player_id'], request['sell'])

                elif 'game' in keys_:
                    data = self.game(request['player_id'], request['game'])

                elif 'logout' in keys_:
                    writer.close()
                    # await writer.wait_closed()
                    logging.debug('Logout {} ({})'.format(request['logout'], addr))
                    break

                if not data:
                    continue

                writer.write(cf.encode(data))
                logging.debug('Server send to {}: {}'.format(addr, data))
                await writer.drain()

        except ConnectionResetError as e:
            print('Connection reset by peer')
            logging.error("ConnectionResetError: {}".format(e.args))
            writer.close()
            # await writer.wait_closed()
        except json.decoder.JSONDecodeError as e:
            print('Uncorrected format')
            logging.error("JSONDecodeError: {}".format(e.args))
            writer.close()
            # await writer.wait_closed()

        finally:
            print("Closed connection from {}".format(addr))

    def login(self, nickname: str) -> dict:
        result = self.db.get_player(nickname=nickname)
        if not result:
            return self.db.create_player(nickname=nickname)
        return result

    def get_items(self, player_id: int) -> dict:
        result = self.db.get_items(player_id)
        return result

    def get_player_items(self, player_id: int) -> dict:
        return self.db.get_player_items(player_id)

    def get_credits(self, player_id: int) -> dict:
        return self.db.get_credits(player_id)

    def buy_item(self, player_id: int, item_id: int) -> dict:
        return self.db.buy_item(player_id, item_id)

    def sell_item(self, player_id: int, item_id: int) -> dict:
        return self.db.sell_item(player_id, item_id)

    def game(self, player_id: int, bet: int) -> dict:
        cr = self.db.get_credits(player_id)['credits']
        if random.randint(1, 100) < cf.pers_win:
            self.db.set_balance(player_id, cr + bet)
            return {'status': 'success'}

        result = max(cr - bet, 50)
        self.db.set_balance(player_id, result)
        return {'status': 'failed'}
