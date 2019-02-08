from .RedisIF import RedisIF

class Shop(object):
    @classmethod
    def set_charge_ratio(cls, id, charge_ratio):
        RedisIF.r.set('tribe:shop:charge_ratio:%d' % id, charge_ratio)

    @classmethod
    def get_charge_ratio(cls, id):
        return RedisIF.r.get('tribe:shop:charge_ratio:%d' % id)

    @classmethod
    def set_brokerage_ratio(cls, id, brokerage_ratio):
        RedisIF.r.set('tribe:shop:brokerage_ratio:%d' % id, brokerage_ratio)

    @classmethod
    def get_brokerage_ratio(cls, id):
        return RedisIF.r.get('tribe:shop:brokerage_ratio:%d' % id)