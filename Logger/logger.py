# -*- encoding:utf-8 -*-
import logging
import urllib, json
from MyAbstract.funtions import post


class Logger:
    logger = logging.getLogger('django')
    logger.setLevel(logging.DEBUG)

    @classmethod
    def Log(cls, level, msg, *args, **kwargs):
        msg = str(msg)

        if level == 'info':
            Logger.logger.info(msg, *args, **kwargs)
        elif level == 'warning':
            Logger.logger.warning(msg, *args, **kwargs)
        elif level == 'error':
            Logger.logger.error(msg, *args, **kwargs)
            url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=wx062e89175e0a76a2&corpsecret=6AMPm7zV3LJOcpjDonZxH9vqkmFgtbxTJ9q7tnIBdDE8yTrFEX-71y01DHP7Y_TE'
            access_token = json.loads(urllib.request.urlopen(url=url).read().decode('utf-8'))['access_token']

            url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % access_token
            postdata = '{ "touser": "zyf", \
                                    "toparty": "@all", \
                                    "totag": "@all", \
                                    "msgtype": "text", \
                                    "agentid": 0, \
                                    "text": { \
                                       "content": "%s" \
                                    }, \
                                    "safe":0 \
                                    }' % msg

            post(url, postdata)
