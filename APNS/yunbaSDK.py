import json
import requests
from rest_framework.response import Response


class YunbaConf(object):
    app_key = ''#
    secret_key = ''#

class YunbaSellerConf(object):
    app_key = ''#
    secret_key = ''#


class YunbaBase(object):
    url = 'http://rest.yunba.io:8080'
    headers = {'content-type': 'application/json'}
    parameters = {}

    def temp_func(self, msg, paras, aps, ios_sound):
        if ios_sound:
            aps["sound"] = ios_sound
        else:
            aps["mutable-content"] = 1

        paras['opts'] = {
            "apn_json": {"aps": aps},
            "third_party_push": {"notification_title": "新牙行", "notification_content": msg}
        }

        response = requests.post(self.url, data=json.dumps(paras).encode(), headers=self.headers)

        return Response(response.content)

    def send_publish2(self, msg, type, ios_sound):
        paras = self.parameters.copy()
        paras['method'] = 'publish2'
        paras['topic'] = 'news'
        paras['msg'] = {"msg": msg, "type": type}

        aps = {"badge": 3, "alert": {"body": msg, "type": type}}

        return self.temp_func(msg, paras, aps, ios_sound)

    def send_publish2_to_alias(self, alias, title, msg, type, time, ios_sound):
        paras = self.parameters.copy()
        paras['method'] = 'publish2_to_alias'
        paras['alias'] = alias
        paras['msg'] = {"title":title, "msg":msg,"type":type,"time":time}

        aps = {"badge": "+1", "alert": {"title":title, "body": msg, "type": type,"time":time}}

        return self.temp_func(msg, paras, aps, ios_sound)

    def send_publish2_to_alias_batch(self, aliases, title, msg, type, ios_sound):
        paras = self.parameters.copy()
        paras['method'] = 'publish2_to_alias_batch'
        paras['aliases'] = aliases
        paras['msg'] = {"title": title, "msg": msg, "type": type}

        aps = {"badge": "+1", "alert": {"title":title, "body": msg, "type": type}}

        return self.temp_func(msg, paras, aps, ios_sound)

class YunbaBuyer(YunbaBase):
    def __init__(self):
        self.parameters['appkey'] = YunbaConf.app_key
        self.parameters['seckey'] = YunbaConf.secret_key

        super(YunbaBuyer, self).__init__()

class YunbaSeller(YunbaBase):
    def __init__(self):
        self.parameters['appkey'] = YunbaSellerConf.app_key
        self.parameters['seckey'] = YunbaSellerConf.secret_key

        super(YunbaSeller, self).__init__()
