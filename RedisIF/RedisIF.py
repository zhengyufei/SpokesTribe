import redis

class RedisIF:
    is_init = False

    @classmethod
    def init_cls(cls):
        if cls.is_init:
            return

        cls.pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
        cls.r = redis.Redis(connection_pool=cls.pool)

        cls.is_init = True
