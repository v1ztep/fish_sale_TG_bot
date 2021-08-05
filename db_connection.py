import os

import redis

_database = None


def get_database_connection():
    global _database
    if _database is None:
        redis_password = os.getenv("REDIS_DB_PASS")
        redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
        _database = redis.Redis(host=redis_host, port=redis_port,
                                password=redis_password)
    return _database