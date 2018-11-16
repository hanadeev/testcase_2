import json


""" Settings for coordinated work ClientCarCenter и ServerCarCenter """
_max_buffer = 4096                  # Receive buffer for socket

default_credits = 500               # Default credits when creating a user
pers_win = 80                       # Win percentage of the game

base_name = 'game_storage.sqlite3'  # Name database

host = '127.0.0.1'                  # Server parameters
port = 9099


def encode(d: dict) -> bytes:       # Necessary for equal encode/decode
    j = json.dumps(d, ensure_ascii=False)
    return j.encode('utf-8')


def decode(b: bytes) -> dict:
    return json.loads(b, encoding='utf-8')


items = (
    {'name': 'galeon', 'price': 400},
    {'name': 'brig', 'price': 150},
    {'name': 'pistol', 'price': 50},
    {'name': 'sword', 'price': 40},
    {'name': 'helmet', 'price': 60},
    {'name': 'armor', 'price': 100},
    {'name': 'gundum', 'price': 700},
    {'name': 'teddy bear', 'price': 4000},
)