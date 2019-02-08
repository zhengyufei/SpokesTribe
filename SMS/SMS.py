import top.api
from Logger.logger import Logger

class SMS:
    sign_register_name = '新牙行注册'
    sign_confirm_name = '新牙行验证'
    sign_other = '新牙行'

    register_type = "SMS_78355027"  # 用户注册
    confirm_type = 'SMS_78325017'  # 身份验证验证码
    shop_cash_type = 'SMS_85415070' # 店铺结算转账通知
    shop_first_type = 'SMS_109910001'  # 店铺和账户开通通知
    shop_create_type = 'SMS_109870002'  # 店铺结算转账通知

    def __init__(self):
        self.appkey = ''
        self.secret = ''
        self.product = ''

    def sms(self, phone, code, sign, type):
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))

        req.extend = ""
        req.sms_type = "normal"
        req.sms_free_sign_name = sign
        req.sms_param = "{code:'%s',product:'%s'}" % (code, self.product)
        req.rec_num = phone
        req.sms_template_code = type

        try:
            resp = req.getResponse()
            Logger.Log('info', resp)
        except Exception as e:
            Logger.Log('warning', e)

    def register_sms(self, phone, code):
        self.sms(phone, code, self.sign_register_name, self.register_type)

    def confirm_sms(self, phone, code):
        self.sms(phone, code, self.sign_confirm_name, self.confirm_type)

    def other_sms(self, phone, code):
        self.sms(phone, code, self.sign_other, self.confirm_type)

class SellerSMS(SMS):
    def __init__(self):
        self.appkey = '23536102'
        self.secret = '9603d9342d22bc0ce0aefae94ea2e3a5'
        self.product = '新牙行商家版'

    def cash_sms(self, phone, name, date, cash, bank, num):
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))

        req.extend = ""
        req.sms_type = "normal"
        req.sms_free_sign_name = self.sign_other
        req.sms_param = "{name:'%s', date:'%s', cash:'%s', bank:'%s', num:'%s'}"%(name, date, cash, bank, num)
        req.rec_num = phone
        req.sms_template_code = self.shop_cash_type

        try:
            resp = req.getResponse()
            Logger.Log('info', resp)
        except Exception as e:
            Logger.Log('warning', e)

    def first_sms(self, phone, name, pw):
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))

        req.extend = ""
        req.sms_type = "normal"
        req.sms_free_sign_name = self.sign_other
        req.sms_param = "{name:'%s', user:'%s', pw:'%s'}"%(name, str(phone), pw)
        req.rec_num = phone
        req.sms_template_code = self.shop_first_type

        try:
            resp = req.getResponse()
            Logger.Log('info', resp)
        except Exception as e:
            Logger.Log('warning', e)

    def create_sms(self, phone, name):
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))

        req.extend = ""
        req.sms_type = "normal"
        req.sms_free_sign_name = self.sign_other
        req.sms_param = "{name:'%s'}"%(name)
        req.rec_num = phone
        req.sms_template_code = self.shop_create_type

        try:
            resp = req.getResponse()
            Logger.Log('info', resp)
        except Exception as e:
            Logger.Log('warning', e)

class SpokesmanSMS(SMS):
    def __init__(self):
        self.appkey = '23534989'
        self.secret = 'caeeb08a682dd7ef8442cc3c0a13313b'
        self.product = '新牙行'
