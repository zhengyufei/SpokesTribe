from .RedisIF import RedisIF

class GlobalVar(object):
    is_init = False

    @classmethod
    def init_cls(cls):
        if cls.is_init:
            return

        RedisIF.r.set('tribe:globa:ali_count', 10)

        cls.is_init = True

    @classmethod
    def decr_ali_count(cls):
        return RedisIF.r.decr('tribe:globa:ali_count')
