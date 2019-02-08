import datetime, hashlib, base64, rsa, json
import SpokesTribe.settings as settings
from urllib import request,parse
import time
from Crypto.Cipher import AES
from binascii import a2b_hex, b2a_hex
import hashlib
from common.models import Trade, TradeShop


class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_ECB
        BS = AES.block_size
        self.pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        self.unpad = lambda s: s[0:-ord(s[-1])]

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode)
        encrypted = cryptor.encrypt(self.pad(text))
        return b2a_hex(encrypted)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return self.unpad(plain_text.decode())

class PayConf(object):
    weixin_type = 'WeixinCDZH'
    ali_type = 'AlipayCDZH'
    mine_open_id = ''#
    mine_open_key = ''#
    mine_password = '123456'

    @classmethod
    def get_notify_url(cls, trade_number):
        return "https://{0}:{1}/common/paycallback/{2}/zhaobankpay/".format(
            settings.DOMAIN_NAME, settings.PAY_BACK_PORT, trade_number)

    @classmethod
    def get_jump_url_discount(cls, token, type, trade_number):
        return "http://www.dailibuluo.com/WeixinDevelop/PayRequestDispatcher.jsp?" \
               "token={0}&from={1}&trade_number={2}".format(token, type, trade_number)

    @classmethod
    def get_jump_url_other(cls, token, type, shop_id, spokesman_id):
        return "http://www.dailibuluo.com/WeixinDevelop/PayRequestDispatcher.jsp?" \
               "token={0}&from={1}&shop_id={2}&spokesman_id={3}".format(token, type, shop_id, spokesman_id)

    @classmethod
    def get_notify_url_shop(cls, trade_number):
        return "https://{0}:{1}/common/paycallback/{2}/shop_zhaobankpay/".format(
            settings.DOMAIN_NAME, settings.PAY_BACK_PORT, trade_number)

    @classmethod
    def get_jump_url_shop(cls, token, type, shop_id, trade_number):
        return "http://www.dailibuluo.com/Shop_Wx/rechargeDispatcher.jsp?" \
               "token={0}&from={1}&shop_id={2}&trade_number={3}".format(token, type, shop_id, trade_number)

class Common_util_pub(object):
    url = None
    data = {}

    def __init__(self, open_id, open_key):
        self.open_key = open_key

        self.parameters = {}
        self.parameters['open_id'] = open_id
        self.parameters['timestamp'] = str(int(time.time()))

    def formatBizQueryParaMap(self, paraMap, urlencode=False):
        slist = sorted(paraMap)
        buff = []
        for k in slist:
            v = parse.quote(paraMap[k]) if urlencode else paraMap[k]
            if v:
                buff.append("%s=%s" % (k, v))
        return "&".join(buff)

    def getData(self):
        pc = prpcrypt(self.open_key)  # 初始化密钥
        encode_json = json.dumps(self.data)
        encrypt_buf = pc.encrypt(encode_json)
        self.parameters['data'] = encrypt_buf.decode()
        pc2 = prpcrypt(self.open_key)  # 初始化密钥
        cmd = dict.copy(self.parameters)
        cmd['open_key'] = self.open_key
        content = self.formatBizQueryParaMap(cmd)
        hash = hashlib.sha1(content.encode()).hexdigest()
        m2 = hashlib.md5()
        m2.update(hash.encode('utf-8'))
        sign = m2.hexdigest()
        self.parameters['sign'] = sign
        return self.formatBizQueryParaMap(self.parameters)

    def post(self, second=30):
        data = self.getData()
        return request.urlopen(url=self.url, data=data.encode(), timeout=second).read()

    def getResponse(self):
        response = self.post()
        result = json.loads(response.decode())
        pc = prpcrypt(self.open_key)

        if result['errcode'] == 0:
            result = json.loads(pc.decrypt(result['data']))

        return result

class List(Common_util_pub):
    def __init__(self, open_id, open_key):
        self.url = 'https://api.tlinx.com/mct1/paylist'

        self.data['pmt_type'] = '4'

        super(List, self).__init__(open_id, open_key)

class Pay(Common_util_pub):
    def __init__(self, open_id, open_key, trade_number, type, amount, token, jump, *args, **kwargs): #shop_id=None, spoker_id=None
        self.url = 'https://api.tlinx.com/mct1/payorder'

        self.data['out_no'] = str(trade_number)
        pmt_tag = PayConf.weixin_type if type == 6 else PayConf.ali_type
        self.data['pmt_tag'] = pmt_tag #WeixinCDZH, AlipayCDZH
        self.data['original_amount'] = int(amount*100)
        self.data['trade_amount'] = int(amount*100)


        if jump in ['discount', 'other']:
            self.data['notify_url'] = PayConf.get_notify_url(trade_number)
        elif 'shop' == jump:
            self.data['notify_url'] = PayConf.get_notify_url_shop(trade_number)

        if 'discount' == jump:
            self.data['jump_url'] = PayConf.get_jump_url_discount(token, type, trade_number)
        elif 'other' == jump:
            self.data['jump_url'] = PayConf.get_jump_url_other(token, type, kwargs['shop_id'], kwargs['spoker_id'])
        elif 'shop' == jump:
            self.data['jump_url'] = PayConf.get_jump_url_shop(token, type, kwargs['shop_id'], trade_number)

        super(Pay, self).__init__(open_id, open_key)

class Refund(Common_util_pub):
    def __init__(self, open_id, open_key, password, trade_number, zhaobank_no, refund_id, amount):
        self.url = 'https://api.tlinx.com/mct1/payrefund'

        self.data['out_no'] = str(trade_number)
        self.data['ord_no'] = zhaobank_no
        self.data['refund_ord_no'] = refund_id
        self.data['refund_amount'] = int(amount * 100)
        self.data['shop_pass'] = hashlib.sha1(password.encode()).hexdigest()

        super(Refund, self).__init__(open_id, open_key)

class AbstractCallBack(object):
    parameters = {}
    data = {}

    def __init__(self, data):
        self.data = data

    def formatBizQueryParaMap(self, paraMap, urlencode=False):
        slist = sorted(paraMap)
        buff = []
        for k in slist:
            v = parse.quote(paraMap[k]) if urlencode else paraMap[k]
            if v:
                buff.append("%s=%s" % (k, v))
        return "&".join(buff)

    def CheckSign(self):
        cmd = dict.copy(self.data)

        sign = cmd['sign']
        del cmd['sign']

        trade = self.trade_class.objects.get(trade_number=self.data['out_no'])
        #根据订单号查到出open_key
        cmd['open_key'] = trade.shop.zhaoshang.open_key

        content = self.formatBizQueryParaMap(cmd)
        hash = hashlib.sha1(content.encode()).hexdigest()
        m2 = hashlib.md5()
        m2.update(hash.encode('utf-8'))
        sign2 = m2.hexdigest()

        return True
        return sign == sign2

class CallBack(AbstractCallBack):
    def __init__(self, data):
        self.trade_class = Trade

        super(CallBack, self).__init__(data)


class ShopCallBack(AbstractCallBack):
    def __init__(self, data):
        self.trade_class = TradeShop

        super(ShopCallBack, self).__init__(data)
