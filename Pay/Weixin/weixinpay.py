# coding:utf-8

import json
import time
import random
from urllib import request,parse
import hashlib
import threading
import xml.etree.ElementTree as ET
import io
import pycurl
import os
from SpokesTribe.settings import BASE_DIR, DOMAIN_NAME, PAY_BACK_PORT


class BaseConf(object):
    TIMEOUT = 30

class BuyerConf(BaseConf):
    APPID = ''#
    MCHID = ''#
    KEY = ''#
    SSLCERT_PATH = os.path.join(BASE_DIR, 'Pay/Weixin/apiclient_cert.pem')
    SSLKEY_PATH = os.path.join(BASE_DIR, 'Pay/Weixin/apiclient_key.pem')

class BuyerJSConf(object):
    APPID = ''#
    MCHID = ''#
    KEY = ''#
    SSLCERT_PATH = os.path.join(BASE_DIR, 'Pay/WeixinApi/js_apiclient_cert.pem')
    SSLKEY_PATH = os.path.join(BASE_DIR, 'Pay/WeixinApi/js_apiclient_key.pem')

class SellerConf(BaseConf):
    APPID = ''#
    MCHID = ''#
    KEY = ''#
    SSLCERT_PATH = os.path.join(BASE_DIR, 'Pay/Weixin/shop_apiclient_cert.pem')
    SSLKEY_PATH = os.path.join(BASE_DIR, 'Pay/Weixin/shop_apiclient_key.pem')

class HttpClient(object):
    def __init__(self, conf):
        self.conf = conf

    def get(self, url, second=30):
        return self.postXml(url, second)

    def postXml(self, xml, url, second=30):
        """不使用证书"""
        data = request.urlopen(url, xml.encode(), timeout=second).read()
        return data

    def postXmlSSL(self, xml, url, cert=True, post=True):
        """使用证书"""
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.SSL_VERIFYHOST, False)
        self.curl.setopt(pycurl.SSL_VERIFYPEER, False)
        # 设置不输出header
        self.curl.setopt(pycurl.HEADER, False)
        self.curl.setopt(pycurl.URL, url)

        # 设置证书
        # 使用证书：cert 与 key 分别属于两个.pem文件
        # 默认格式为PEM，可以注释
        if cert:
            self.curl.setopt(pycurl.SSLKEYTYPE, "PEM")
            self.curl.setopt(pycurl.SSLCERTTYPE, "PEM")
            self.curl.setopt(pycurl.SSLKEY, self.conf.SSLKEY_PATH)
            self.curl.setopt(pycurl.SSLCERT, self.conf.SSLCERT_PATH)

        # post提交方式
        if post:
            self.curl.setopt(pycurl.POST, True)
            self.curl.setopt(pycurl.POSTFIELDS, xml)
        buff = io.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, buff.write)

        self.curl.perform()
        return buff.getvalue()

class AbstractPub(object):
    """所有接口的基类"""

    def trimString(self, value):
        if not value:
            value = ''
        return value

    def createNoncestr(self, length=32):
        """产生随机字符串，不长于32位"""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        strs = []
        for x in range(length):
            strs.append(chars[random.randrange(0, len(chars))])
        return "".join(strs)

    def formatBizQueryParaMap(self, paraMap, urlencode):
        """格式化参数，签名过程需要使用"""
        slist = sorted(paraMap)
        buff = []
        for k in slist:
            v = parse.quote(paraMap[k]) if urlencode else paraMap[k]
            if v:
                buff.append("%s=%s" % (k, v))
        return "&".join(buff)

    def getSign(self, dic, key):
        """生成签名"""
        cmd = dict.copy(dic)
        cmd.pop('sign', None)
        # 签名步骤一：按字典序排序参数,formatBizQueryParaMap已做
        String = self.formatBizQueryParaMap(cmd, False)
        # 签名步骤二：在string后加入KEY

        String = "%s&key=%s" % (String, key)
        # 签名步骤三：MD5加密
        String = hashlib.md5(String.encode()).hexdigest()
        # 签名步骤四：所有字符转为大写
        result_ = String.upper()
        return result_

    def arrayToXml(self, arr):
        """array转xml"""
        xml = ["<xml>"]
        for k, v in arr.items():
            if isinstance(v,int):
                xml.append("<{0}>{1}</{0}>".format(k, v))
            else:
                xml.append("<{0}><![CDATA[{1}]]></{0}>".format(k, v))
        xml.append("</xml>")
        return "".join(xml)

    def xmlToArray(self, xml):
        """将xml转为array"""
        array_data = {}
        root = ET.fromstring(xml)
        for child in root:
            value = child.text
            array_data[child.tag] = value
        return array_data

    def postXmlCurl(self, xml, url, second=30):
        """以post方式提交xml到对应的接口url"""
        return HttpClient(self.conf).postXml(xml, url, second=second)

    def postXmlSSLCurl(self, xml, url):
        """使用证书，以post方式提交xml到对应的接口url"""
        return HttpClient(self.conf).postXmlSSL(xml, url)

class PayApi(AbstractPub):
    #parameters = None  # jsapi参数，格式为json
    #prepay_id = None  # 使用统一支付接口得到的预支付id
    #curl_timeout = None  # curl超时时间

    def __init__(self, conf):
        self.conf = conf
        self.curl_timeout = conf.TIMEOUT

    def setPrepayId(self, prepayId):
        """设置prepay_id"""
        self.prepay_id = prepayId

class ClientApi(PayApi):
    def getParameters(self):
        obj = {}
        obj["appid"] = self.conf.APPID
        obj["partnerid"] = self.conf.MCHID
        obj["prepayid"] = self.prepay_id
        obj["timestamp"] = "{0}".format(int(time.time()))
        obj["noncestr"] = self.createNoncestr()
        obj["package"] = "Sign=WXPay"
        obj["sign"] = self.getSign(obj, key=self.conf.KEY)
        self.parameters = json.dumps(obj)

        return self.parameters

class JsApi(PayApi):
    def getParameters(self):
        obj = {}
        obj["appId"] = self.conf.APPID
        obj["timeStamp"] = "{0}".format(int(time.time()))
        obj["nonceStr"] = self.createNoncestr()
        obj["package"] = "prepay_id={0}".format(self.prepay_id)
        obj["signType"] = "MD5"
        obj["paySign"] = self.getSign(obj, key=self.conf.KEY)
        self.parameters = json.dumps(obj)

        return self.parameters

class ClientPub(AbstractPub):
    """请求型接口的基类"""
    response = None  # 微信返回的响应
    url = None  # 接口链接
    curl_timeout = None  # curl超时时间
    fields = []

    def __init__(self, conf):
        self.conf = conf
        self.curl_timeout = conf.TIMEOUT
        self.parameters = {}  # 请求参数，类型为关联数组
        self.result = {}  # 返回参数，类型为关联数组

    def setParameter(self, parameter, parameterValue):
        """设置请求参数"""
        self.parameters[self.trimString(parameter)] = self.trimString(parameterValue)

    def updateParameter(self, **kwargs):
        for key in kwargs:
            self.setParameter(key, kwargs[key])

    def createXml(self):
        """生成接口参数xml"""
        # 检测必填参数
        if any(self.parameters.get(key) is None for key in self.fields):
            raise ValueError("missing parameter")

        self.parameters["nonce_str"] = self.createNoncestr()  # 随机字符串
        self.parameters["appid"] = self.conf.APPID  # 公众账号ID
        self.parameters["mch_id"] = self.conf.MCHID  # 商户号
        self.parameters["sign"] = self.getSign(self.parameters, key=self.conf.KEY)  # 签名

        return self.arrayToXml(self.parameters)

    def postXml(self):
        """post请求xml"""
        xml = self.createXml()
        self.response = self.postXmlCurl(xml, self.url, self.curl_timeout)
        return self.response

    def postXmlSSL(self):
        """使用证书post请求xml"""
        xml = self.createXml()
        self.response = self.postXmlSSLCurl(xml, self.url)
        return self.response

    def getResult(self):
        """获取结果，默认不使用证书"""
        self.postXml()
        self.result = self.xmlToArray(self.response)

        return self.result

class UnifiedOrderPub(ClientPub):
    """统一支付接口类"""
    url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    fields = ['out_trade_no', 'body', 'total_fee', 'notify_url', 'trade_type']

class RefundPub(ClientPub):
    """退款申请接口"""
    url = "https://api.mch.weixin.qq.com/secapi/pay/refund"
    fields = ['out_trade_no', 'out_refund_no', 'total_fee', 'refund_fee', 'op_user_id']

    def getResult(self):
        """ 获取结果，使用证书通信(需要双向证书)"""
        self.postXmlSSL()
        self.result = self.xmlToArray(self.response)
        return self.result

class ServerPub(AbstractPub):
    """响应型接口基类"""
    SUCCESS, FAIL = "SUCCESS", "FAIL"

    def __init__(self, conf):
        self.key = conf.KEY
        self.data = {}  # 接收到的数据，类型为关联数组
        self.returnParameters = {}  # 返回参数，类型为关联数组

    def saveData(self, xml):
        """将微信的请求xml转换成关联数组，以方便数据处理"""
        self.data = self.xmlToArray(xml)

    def checkSign(self):
        """校验签名"""
        tmpData = dict(self.data)  # make a copy to save sign
        del tmpData['sign']
        sign = self.getSign(tmpData, key=self.key)  # 本地签名
        if self.data['sign'] == sign:
            return True
        return False

    def getData(self):
        """获取微信的请求数据"""
        return self.data

    def setReturnParameter(self, parameter, parameterValue):
        """设置返回微信的xml数据"""
        self.returnParameters[self.trimString(parameter)] = self.trimString(parameterValue)

    def createXml(self):
        """生成接口参数xml"""
        return self.arrayToXml(self.returnParameters)

    def returnXml(self):
        """将xml数据返回微信"""
        returnXml = self.createXml()
        return returnXml

class NotifyPub(ServerPub):
    """通用通知接口"""

    def updateReturnParameter(self, **kwargs):
        for key in kwargs:
            self.setReturnParameter(key, kwargs[key])

class PayCallback(object):
    # 回调接口
    parameters = {}

    def __init__(self, conf, data):
        self.conf = conf
        self.notify = NotifyPub(self.conf)
        self.notify.saveData(data.decode('utf-8'))
        self.parameters = self.notify.getData()

    def check_sign(self):
        return self.notify.checkSign()

    def get_data(self):
        return self.parameters

    def get_number(self):
        return self.parameters['out_trade_no']

    def is_success(self):
        return self.check_sign() and self.parameters.get('result_code', '') == 'SUCCESS'

    def get_response(self):
        if self.parameters.get('result_code', '') == 'SUCCESS':
            self.notify.updateReturnParameter(return_code='SUCCESS', return_msg='')
        else:
            self.notify.updateReturnParameter(return_code='FAIL', return_msg='参数校验失败')

        return self.notify.createXml()

class AbstractPay(object):
    def refund(self, trade_number, total, refund_number, amount, operator):
        pub = RefundPub(self.conf)
        cmd = {'out_trade_no': trade_number,
               'out_refund_no': refund_number,
               'total_fee': int(total * 100),
               'refund_fee': int(amount * 100),
               'op_user_id': operator
               }
        pub.updateParameter(**cmd)

        return pub.getResult()

    def pay_callback(self, data):
        self.callback = PayCallback(self.conf, data)

        return self.callback

    def pay_sign(self, id, number, price):
        pay = UnifiedOrderPub(self.conf)
        cmd = {"out_trade_no": number, "body": '新牙行交易', "total_fee": str(int((price * 100))),  # 单位分
               "notify_url": self.get_notify_url(id),"trade_type": "APP"}
        pay.updateParameter(**cmd)
        res = pay.getResult()

        if res.get('result_code', '') == 'SUCCESS':
            prepay_id = res["prepay_id"]

            client = ClientApi(self.conf)
            client.setPrepayId(prepay_id)

            return client.getParameters()

        return None

class BuyerPay(AbstractPay):
    def __init__(self):
        self.conf = BuyerConf()

    def get_notify_url(self, id):
        return 'https://{0}:{1}/common/paycallback/{2}/weixinpay/'.format(DOMAIN_NAME, PAY_BACK_PORT, id)

class BuyerJSPay(AbstractPay):
    def __init__(self):
        self.conf = BuyerJSConf()

    def get_notify_url(self, id):
        return 'https://{0}:{1}/common/paycallback/{2}/weixinpay/'.format(DOMAIN_NAME, PAY_BACK_PORT, id)

class SellerPay(AbstractPay):
    def __init__(self):
        self.conf = SellerConf()

    def get_notify_url(self, id):
        return 'https://{0}:{1}/common/paycallback/{2}/shop_weixinpay/'.format(DOMAIN_NAME, PAY_BACK_PORT, id)
