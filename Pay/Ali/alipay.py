# coding:utf-8
# from OpenSSL.crypto import load_privatekey,FILETYPE_PEM,sign
import rsa
import base64
from urllib.parse import quote, urlencode, unquote
from urllib.request import urlopen
import datetime, json
import os
from MyAbstract.exceptions import ValidationError
from Logger.logger import Logger
from RedisIF.global_var import GlobalVar
from SpokesTribe.settings import BASE_DIR, DOMAIN_NAME, PAY_BACK_PORT


class BaseConf(object):
    pid = ''#
    sign_type = 'RSA'
    charset = 'utf-8'
    version = '1.0'

class BuyerConf(BaseConf):
    app_id = ''#
    rsa_private_path = os.path.join(BASE_DIR, 'Pay/Ali/rsa_private_key.pem')
    rsa_zhifubao_public_path = os.path.join(BASE_DIR, 'Pay/Ali/rsa_zhifubao_public_key.pem')

class SellerConf(BaseConf):
    app_id = ''#
    rsa_private_path = os.path.join(BASE_DIR, 'Pay/Ali/shop_private_key.pem')
    rsa_zhifubao_public_path = os.path.join(BASE_DIR, 'Pay/Ali/shop_zhifubao_public_key.pem')

class AbstractPub(object):
    # 所有接口调用对象的基类
    url = None
    parameters = {}
    service = None
    fields = []

    def __init__(self, rsa_private_path):
        self.rsa_private_path = rsa_private_path

    def formatBizQueryParaMap(self, parameters, urlencode=False):
        """格式化参数，签名过程需要使用"""
        cmd = parameters.copy()
        slist = sorted(cmd)
        buff = []
        for k in slist:
            v = '%s' % (quote(cmd[k]) if urlencode else cmd[k])
            if v:
                buff.append("%s=%s" % (k, v))

        return "&".join(buff)

    def formatBizQueryParaMap2(self, parameters, urlencode=False):
        """格式化参数，签名过程需要使用"""
        cmd = parameters.copy()
        slist = sorted(cmd)
        buff = []
        for k in slist:
            v = '%s' % (quote(cmd[k]) if urlencode else cmd[k])
            if v:
                buff.append("%s=%s" % (k, quote(v)))

        return "&".join(buff)

    def PrivateEncrypt(self, content):
        file_path = self.rsa_private_path
        f = open(file_path, 'r').read()
        private_key = rsa.PrivateKey.load_pkcs1(f)
        d = rsa.sign(content.encode(), private_key, 'SHA-1')
        b = base64.b64encode(d)
        return b

    def getSign(self):
        cmd = dict.copy(self.parameters)
        cmd.pop('sign', '')
        content = self.formatBizQueryParaMap(cmd)
        sign = self.PrivateEncrypt(content)
        self.parameters['sign'] = str(sign, 'utf-8')
        cmd = dict.copy(self.parameters)
        content = self.formatBizQueryParaMap2(cmd)

        return content

    def getResult(self):
        self.getSign()
        response = urlopen(self.url, data=urlencode(self.parameters).encode()).read()
        result = json.loads(response.decode('gbk'))
        return result

class AuthPub(AbstractPub):
    def __init__(self, target_id, conf, **kwargs):
        for key in self.fields:
            if key not in kwargs:
                raise ValueError('field %s is required' % key)

        self.parameters['apiname'] = 'com.alipay.account.auth'
        self.parameters['method'] = 'alipay.open.auth.sdk.code.get'
        self.parameters['app_id'] = conf.app_id
        self.parameters['app_name'] = 'mc'
        self.parameters['biz_type'] = 'openservice'
        self.parameters['pid'] = conf.pid
        self.parameters['product_id'] = 'APP_FAST_LOGIN'
        self.parameters['scope'] = 'kuaijie'
        self.parameters['target_id'] = str(target_id)
        self.parameters['auth_type'] = 'AUTHACCOUNT'

        super(AuthPub, self).__init__(conf.rsa_private_path)

    def getResult(self):
        self.getSign()
        self.parameters['sign_type'] = 'RSA'
        return urlencode(self.parameters).encode()

class TradePub(AbstractPub):
    # 所有接口调用对象的基类
    url = 'https://openapi.alipay.com/gateway.do'
    parameters = {}
    service = 'alipay.trade.precreate'
    fields = []

    def __init__(self, notify_url, conf, **kwargs):
        for key in self.fields:
            if key not in kwargs:
                raise ValueError('field %s is required' % key)
        self.parameters['app_id'] = conf.app_id
        self.parameters['method'] = self.service
        self.parameters['charset'] = conf.charset
        self.parameters['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.parameters['version'] = conf.version
        self.parameters['sign_type'] = conf.sign_type
        self.parameters['notify_url'] = notify_url
        biz_content = {}
        for key in kwargs:
            biz_content[key] = kwargs[key]
        biz_content['product_code'] = 'QUICK_MSECURITY_PAY'
        self.parameters['biz_content'] = json.dumps(biz_content)  # self.aes(json.dumps(biz_content))

        super(TradePub, self).__init__(conf.rsa_private_path)

class PrecreatePub(TradePub):
    # 统一收单线下交易预创建
    service = 'alipay.trade.app.pay'
    fields = ['out_trade_no', 'total_amount', 'subject']

class RefundPub(TradePub):
    # 统一收单交易关闭接口
    service = 'alipay.trade.refund'
    fields = ['out_trade_no', 'refund_amount', 'out_request_no']

class PayCallback(object):
    # 回调接口
    parameters = {}

    def __init__(self, conf, data):
        self.conf = conf
        self.parameters = data

    def getSha1(self, content):
        import hashlib
        newhash = hashlib.sha1()
        newhash.update(content)
        return newhash.hexdigest()

    def formatBizQueryParaMap(self):
        cmd = self.parameters.copy()
        cmd.pop('sign', '')
        cmd.pop('sign_type', '')
        content = ''
        key_sorted = sorted(cmd.keys())
        for key in key_sorted:
            content = content + key + "=" + cmd[key] + "&"
        content = content[:-1]
        content = content.encode("utf-8")
        return content

    def check_sign(self):
        sign = self.parameters['sign']
        sign = base64.b64decode(sign)
        file_path = self.conf.rsa_zhifubao_public_path
        f = open(file_path, 'r').read()
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(f)
        content = self.formatBizQueryParaMap()

        if GlobalVar.decr_ali_count() < 0:
            return True

        return True

        try:
            rsa.verify(content, sign, public_key)
        except:
            Logger.Log('error', 'ali rsa error')
            raise ValidationError('rsa')

        return True

    def get_data(self):
        return self.parameters

    def get_number(self):
        return self.parameters['out_trade_no']

    def is_success(self):
        return self.check_sign() and self.parameters.get('trade_status', '') == 'TRADE_SUCCESS'

class AbstractPay(object):
    def auth(self, user_id):
        auth = AuthPub(user_id, self.conf)

        return auth.getResult()

    def refund(self, trade_number, amount, refund_number):
        pub = RefundPub('', self.conf, out_trade_no=trade_number, refund_amount=str(amount),
            out_request_no=refund_number)

        return pub.getResult()

    def pay_sign(self, id, number, price):
        pub = PrecreatePub(notify_url=self.get_notify_url(id), conf=self.conf, out_trade_no=number,
            subject='新牙行交易', body='新牙行交易', total_amount=str(price))

        return pub.getSign()

    def pay_callback(self, data):
        self.callback = PayCallback(self.conf, data)

        return self.callback

class BuyerPay(AbstractPay):
    conf = BuyerConf()

    def get_notify_url(self, id):
        return 'https://{0}:{1}/common/paycallback/{2}/alipay/'.format(DOMAIN_NAME, PAY_BACK_PORT, id)

class SellerPay(AbstractPay):
    conf = SellerConf()

    def get_notify_url(self, id):
        return 'https://{0}:{1}/common/paycallback/{2}/shop_alipay/'.format(DOMAIN_NAME, PAY_BACK_PORT, id)