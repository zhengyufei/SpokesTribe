def init():
    from .RedisIF import RedisIF
    RedisIF.init_cls()
    from .global_var import GlobalVar
    GlobalVar.init_cls()