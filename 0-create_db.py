#!/usr/bin/python3

import server

if __name__ == '__main__':
    db = server.DataBase()
    db.create_tables()
    db.create_items()
    db.close()

