import json
import SpokesTribe.settings as settings
import time
import hashlib
import requests
from urllib import parse


class PayConf(object):
    pay_ver = '100'
    weixin_type = '010'
    ali_type = '020'
    qq_type = '060'
    jd_type = '080'

    url = 'https://pay.lcsw.cn/lcsw'

    @classmethod
    def get_notify_url(cls, trade_number):
        return "https://{0}:{1}/common/paycallback/{2}/fuyoupay/".format(
            settings.DOMAIN_NAME, settings.PAY_BACK_PORT, trade_number)

    @classmethod
    def get_notify_url_shop(cls, trade_number):
        return "https://{0}:{1}/common/paycallback/{2}/shop_fuyoupay/".format(
            settings.DOMAIN_NAME, settings.PAY_BACK_PORT, trade_number)

class Common_util_pub(object):
    def __init__(self, merchant_no, terminal_id, access_token, trade_no):
        self.access_token = access_token

        self.parameters['pay_ver'] = PayConf.pay_ver
        self.parameters['merchant_no'] = merchant_no
        self.parameters['terminal_id'] = terminal_id
        self.parameters['terminal_trace'] = trade_no
        self.parameters['terminal_time'] = str(int(time.time()))

    def generateKey(self):
        buff = []
        for t in self.fields:
            buff.append("%s=%s" % (t, self.parameters[t]))
        buff.append("%s=%s" % ('access_token', self.access_token))
        temp = "&".join(buff)
        key_sign = hashlib.md5(temp.encode()).hexdigest()

        return key_sign

    def getData(self):
        self.parameters['key_sign'] = self.generateKey()

        return json.dumps(self.parameters)

    def post(self, second=30):
        data = self.getData()
        print('test2', data)
        headers = {'content-type': 'application/json'}
        return requests.post(url=self.url, headers=headers, data=data.encode(), timeout=second).content

    def getResponse(self):
        response = self.post()
        result = json.loads(response.decode())

        #if result['errcode'] == 0:
        #    result = json.loads(pc.decrypt(result['data']))

        return result

class RegisterToken(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, trade_no):
        self.fields = ('pay_ver', 'service_id', 'merchant_no', 'terminal_id', 'terminal_trace',
                       'terminal_time')

        self.url = PayConf.url + '/pay/100/sign'

        self.parameters = {}
        self.parameters['service_id'] = merchant_no

        super(RegisterToken, self).__init__(merchant_no, terminal_id, None, trade_no)

    def generateKey(self):
        buff = []
        for t in self.fields:
            buff.append("%s=%s" % (t, self.parameters[t]))
        temp = "&".join(buff)
        key_sign = hashlib.md5(temp.encode()).hexdigest()

        return key_sign

class BarcodePay(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, access_token, trade_no, pay_type, total_fee, auto_no):
        self.fields = ('pay_ver', 'pay_type', 'service_id', 'merchant_no', 'terminal_id', 'terminal_trace',
                       'terminal_time', 'auth_no', 'total_fee')

        self.url = PayConf.url + '/pay/100/barcodepay'

        self.parameters = {}
        self.parameters['pay_type'] = pay_type
        self.parameters['service_id'] = '010'

        self.parameters['total_fee'] = total_fee
        self.parameters['auth_no'] = auto_no

        super(BarcodePay, self).__init__(merchant_no, terminal_id, access_token, trade_no)

class JsPay(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, access_token, shop_name, trade_no, pay_type, total_fee, open_id, notify_url):
        self.fields = ('pay_ver', 'pay_type', 'service_id', 'merchant_no', 'terminal_id', 'terminal_trace',
                       'terminal_time', 'total_fee')

        self.url = PayConf.url + '/pay/100/jspay'

        self.parameters = {}
        self.parameters['pay_type'] = pay_type
        self.parameters['service_id'] = '012'

        self.parameters['total_fee'] = str(int(total_fee * 100))
        self.parameters['open_id'] = open_id
        self.parameters['order_body'] = shop_name
        self.parameters['notify_url'] = notify_url

        super(JsPay, self).__init__(merchant_no, terminal_id, access_token, trade_no)

    def tempFunc(self, appid, timeStamp, nonceStr, package, signType, paysign):
        obj = {}
        obj["appId"] = appid
        obj["timeStamp"] = timeStamp
        obj["nonceStr"] = nonceStr
        obj["package"] = package
        obj["signType"] = signType
        obj["paySign"] = paysign

        return json.dumps(obj)

class AppPay(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, access_token, trade_no, pay_type, total_fee, notify_url):
        self.fields = ('pay_ver', 'pay_type', 'service_id', 'merchant_no', 'terminal_id', 'terminal_trace',
                      'terminal_time', 'total_fee')

        self.url = PayConf.url + '/pay/110/apppay'

        self.parameters = {}
        self.parameters['pay_type'] = pay_type
        self.parameters['service_id'] = '013'

        self.parameters['total_fee'] = total_fee
        self.parameters['notify_url'] = notify_url

        super(AppPay, self).__init__(merchant_no, terminal_id, access_token, trade_no)

class Openid(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, access_token, redirect_uri):
        self.fields = ('merchant_no', 'redirect_uri', 'terminal_no')

        self.url = PayConf.url + '/wx/jsapi/authopenid'

        self.access_token = access_token

        self.parameters = {}
        self.parameters['merchant_no'] = merchant_no
        self.parameters['terminal_no'] = terminal_id

        self.parameters['redirect_uri'] = redirect_uri

    def get_url(self):
        self.parameters['key_sign'] = self.generateKey()
        return PayConf.url + '/wx/jsapi/authopenid?merchant_no={0}&terminal_no={1}&redirect_uri={2}&key_sign={3}'\
            .format(self.parameters['merchant_no'], self.parameters['terminal_no'],
                    parse.quote(self.parameters['redirect_uri']), self.parameters['key_sign'])

class Refund(Common_util_pub):
    def __init__(self, merchant_no, terminal_id, access_token, refund_no, pay_type, refund_fee, out_trade_no):
        self.fields = ('pay_ver', 'pay_type', 'service_id', 'merchant_no', 'terminal_id', 'terminal_trace',
                       'terminal_time', 'refund_fee', 'out_trade_no')

        self.url = PayConf.url + '/pay/100/refund'

        self.parameters = {}
        self.parameters['pay_type'] = pay_type
        self.parameters['service_id'] = '030'

        self.parameters['refund_fee'] = str(int(refund_fee * 100))
        self.parameters['out_trade_no'] = out_trade_no

        super(Refund, self).__init__(merchant_no, terminal_id, access_token, refund_no)
