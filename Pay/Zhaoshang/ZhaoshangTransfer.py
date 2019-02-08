import datetime, base64, rsa, os, json
from urllib import request,parse
from urllib.parse import quote,urlencode,unquote
from MyAbstract.funtions import RandomNumberString, dictToXml, xmlToDict, privateEncrypt
import SpokesTribe.settings as settings

class TransferConf(object):
    rsa_private_path = os.path.join(settings.BASE_DIR, 'Pay/Zhaoshang/transfer_rsa_private_key.pem')
    rsa_zhaoshang_public_path = os.path.join(settings.BASE_DIR, 'Pay/Zhaoshang/transfer_rsa_zhaoshang_public_key.pem')

    NTBNBR = ''#
    PAYEE_ACC = ''#
    PAYEE_NAME = '成都脸王科技有限公司'
    NOTIFY_URL = 'https://%s:%d/common/paycallback/zhaoshangtransfer/' \
                 % (settings.DOMAIN_NAME, settings.PAY_BACK_PORT)

class Common_util_pub(object):
    url = None
    parameters = {}
    busdat_data = {}

    def __init__(self):
        time_now = datetime.datetime.now()

        self.parameters['NTBNBR'] = TransferConf.NTBNBR
        self.parameters['COMMID'] = RandomNumberString(40)
        self.parameters['SIGTIM'] = time_now.strftime('%Y%m%d%H%M%S0000')

        self.busdat_data["merch_date"] = time_now.strftime('%Y%m%d')
        self.busdat_data["merch_time"] = time_now.strftime('%H%M%S')
        self.busdat_data["currency_no"] = 'RMB'
        self.busdat_data["payee_acc"] = TransferConf.PAYEE_ACC
        self.busdat_data["payee_name"] = TransferConf.PAYEE_NAME
        self.busdat_data["merch_abs"] = "固定信息还是format信息"
        self.busdat_data["back_addr"] = TransferConf.NOTIFY_URL

    def formatBizQueryParaMap(self, paraMap, urlencode=False):
        """格式化参数，签名过程需要使用"""
        slist = ['NTBNBR', 'TRSCOD', 'COMMID', 'SIGTIM', 'BUSDAT']
        buff = []
        for k in slist:
            v = parse.quote(paraMap[k]) if urlencode else paraMap[k]
            if v:
                buff.append("%s=%s" % (k, v))
        return "&".join(buff)

    def getData(self):
        cmd = dict.copy(self.parameters)
        cmd.pop('DATLEN', '')
        content = self.formatBizQueryParaMap(cmd)
        sign = privateEncrypt(TransferConf.rsa_private_path, content)
        self.parameters['SIGDAT'] = sign

        return json.JSONEncoder().encode(self.parameters)

    def post(self, second=30):
        data = self.getData()
        real_data = 'RequestData='+parse.quote(data)
        return request.urlopen(self.url, real_data.encode(), timeout=second).read()

class PayForAnother(Common_util_pub):
    def __init__(self, trade_no, bank_name, acc_no, acc_name, money):
        super(PayForAnother, self).__init__()
        self.url = 'https://b2b.cmbchina.com/CmbBank_B2B/UI/DIDI/DoBusiness.ashx'

        self.parameters['TRSCOD'] = 'CMFK'

        self.busdat_data["merch_serial"] = trade_no
        self.busdat_data["merch_prod"] = "新牙行"
        self.busdat_data["bank_name"] = bank_name
        self.busdat_data["acc_no"] = acc_no
        self.busdat_data["acc_name"] = acc_name
        self.busdat_data["trn_amt"] = int(money * 100)

        print(self.busdat_data)

        xml_data = dictToXml(self.busdat_data)

        self.parameters['BUSDAT'] = str(base64.b64encode(str.encode(xml_data)), 'utf-8')
        self.parameters['DATLEN'] = str(len(self.parameters['BUSDAT']))

class PayCallback(object):
    parameters = {}

    def __init__(self, data):
        dict = json.loads(data['RequestData'])

        for key in dict:
            self.parameters[key] = dict[key]

    def formatBizQueryParaMap(self, paraMap, urlencode=False):
        """格式化参数，签名过程需要使用"""
        slist = ['NTBNBR', 'TRSCOD', 'COMMID', 'SIGTIM', 'BUSDAT']
        buff = []
        for k in slist:
            v = parse.quote(paraMap[k]) if urlencode else paraMap[k]
            if v:
                buff.append("%s=%s" % (k, v))
        return "&".join(buff)

    def CheckSign(self):
        sign = self.parameters['SIGDAT']
        sign = sign.encode("utf-8")
        sign = base64.b64decode(sign)
        file_path = TransferConf.rsa_zhaoshang_public_path
        f = open(file_path, 'r').read()
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(f)
        cmd = self.parameters.copy()
        cmd.pop('DATLEN', '')
        cmd.pop('SIGDAT', '')
        content = self.formatBizQueryParaMap(cmd)
        content = unquote(content)
        content = content.encode("utf-8")

        return rsa.verify(content,sign,public_key)

    def ParseBUSDAT(self):
        xml_data = base64.b64decode(self.parameters['BUSDAT'])
        self.busdat_data = xmlToDict(xml_data)['xml']
        return self.busdat_data

