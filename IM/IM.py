import top.api

from common.models import MyUser
from IM.usersig import admin
import urllib
import json
import random
from Logger.logger import Logger


def post(url, post):
    Logger.Log('info', 'IM post : {0}'.format(post))
    f = urllib.request.urlopen(url, post.encode())
    raw_data = f.read()
    encoding = f.info().get_content_charset('utf8')  # JSON default
    data = json.loads(raw_data.decode(encoding))
    Logger.Log('info', 'IM post return: {0}'.format(data))

    return data

class IM:
    @classmethod
    def batch_add(cls):
        url = 'https://console.tim.qq.com/v4/im_open_login_svc/multiaccount_import?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))

        query = MyUser.objects.all()

        rtn = ''
        Accounts = []

        i = 0
        for user in query:
            i = i + 1
            Accounts.append(str(user.id))

            if i > 99:
                postdata = '{"Accounts":%s}' % (json.dumps(Accounts))
                rtn = rtn + json.dumps(post(url, postdata))

                Accounts = []
                i = 0

        if i > 0:
            postdata = '{"Accounts":%s}' % (json.dumps(Accounts))
            rtn = rtn + json.dumps(post(url, postdata))

        return rtn

    @classmethod
    def add(cls, account, nick, ico):
        url = 'https://console.tim.qq.com/v4/im_open_login_svc/account_import?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
                % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"Identifier":"%s", "Nick":"%s", "FaceUrl":"%s"}'%(account, nick, ico)

        Logger.Log('info', 'add {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def modify_allow_type(cls, account):
        url = 'https://console.tim.qq.com/v4/profile/portrait_set?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","ProfileItem":[{"Tag":"Tag_Profile_IM_AllowType", "Value":"AllowType_Type_NeedConfirm"}]}' % (account)

        Logger.Log('info', 'modify_allow_type {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def modify_nick(cls, account, nick):
        url = 'https://console.tim.qq.com/v4/profile/portrait_set?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","ProfileItem":[{"Tag":"Tag_Profile_IM_Nick", "Value":"%s"}]}' % (account, nick)

        Logger.Log('info', 'modify_nick {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def modify_ico(cls, account, ico):
        url = 'https://console.tim.qq.com/v4/profile/portrait_set?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","ProfileItem":[{"Tag":"Tag_Profile_IM_Image", "Value":"%s"}]}' % (account, ico)

        Logger.Log('info', 'modify_ico {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def modify_major_spokes(cls, account, major):
        url = 'https://console.tim.qq.com/v4/profile/portrait_set?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","ProfileItem":[{"Tag":"Tag_Profile_Custom_SMT", "Value":"%s"}]}' \
                   % (account, major)

        Logger.Log('info', 'modify_major_spokes {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def modify_info(cls, account, nick, ico, major):
        url = 'https://console.tim.qq.com/v4/profile/portrait_set?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","ProfileItem":[{"Tag":"Tag_Profile_IM_AllowType", "Value":"AllowType_Type_NeedConfirm"}, \
        {"Tag":"Tag_Profile_IM_Image", "Value":"%s"}, {"Tag":"Tag_Profile_IM_Image", "Value":"%s"} \
        {"Tag":"Tag_Profile_Custom_SMT", "Value":"%s"}]}' % (account, nick, ico, major)

        Logger.Log('info', 'modify_info {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def get_userinfo(cls, account):
        url = 'https://console.tim.qq.com/v4/profile/portrait_get?usersig=%s&identifier=%s&sdkappid=%d&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"To_Account":["%s"],"TagList":["Tag_Profile_IM_Nick","Tag_Profile_IM_Image","Tag_Profile_Custom_SMT"]}' \
                   % (account)

        return post(url, postdata)

    @classmethod
    def add_friend(cls, from_account, to_account):
        url = 'https://console.tim.qq.com/v4/sns/friend_add?usersig=%s&identifier=%s&sdkappid=%s&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s", "AddFriendItem": [{"To_Account":"%s", "GroupName":"", "AddSource":"AddSource_Type_SERVER"}], "AddType":"Add_Type_Both", "ForceAddFlags":1}' \
            %(from_account, to_account)

        Logger.Log('info', 'add_friend {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def add_friend_one_side(cls, from_account, to_account):
        url = 'https://console.tim.qq.com/v4/sns/friend_add?usersig=%s&identifier=%s&sdkappid=%s&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s", "AddFriendItem": [{"To_Account":"%s", "GroupName":"好友", "AddSource":"AddSource_Type_SERVER"}], "AddType":"Add_Type_Single", "ForceAddFlags":1}' \
                   % (from_account, to_account)

        Logger.Log('info', 'add_friend_one_side {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def del_friend(cls, from_account, to_account):
        url = 'https://console.tim.qq.com/v4/sns/friend_delete?usersig=%s&identifier=%s&sdkappid=%s&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s","To_Account":["%s"],"DeleteType":"Delete_Type_Both"}' \
                   % (from_account, to_account)

        Logger.Log('info', 'del_friend {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def del_all_friends(cls, from_account):
        url = 'https://console.tim.qq.com/v4/sns/friend_delete_all?usersig=%s&identifier=%s&sdkappid=%s&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))
        postdata = '{"From_Account":"%s"}' % (from_account)

        Logger.Log('info', 'del_all_friend {0}'.format(postdata))

        return post(url, postdata)

    @classmethod
    def import_friend(cls, from_account, dict_group):
        url = 'https://console.tim.qq.com/v4/sns/friend_import?usersig=%s&identifier=%s&sdkappid=%s&random=%d&contenttype=json' \
              % (admin(), 'zhengyufei', 1400021429, random.randint(0, 100000000))

        str = None
        for key, value in dict_group.items():
            group_name = key
            if group_name == '客人':
                for item2 in value:
                    if not str:
                        str = '{"To_Account":"%s", "Remark":"%s", "AddSource":"AddSource_Type_SERVER"}' \
                              % (item2[0], item2[1])
                    else:
                        str += ',{"To_Account":"%s", "Remark":"%s", "AddSource":"AddSource_Type_SERVER"}' \
                               % (item2[0], item2[1])
            else:
                for item2 in value:
                    if not str:
                        str = '{"To_Account":"%s", "Remark":"%s", "GroupName":["%s"], "AddSource":"AddSource_Type_SERVER"}' \
                              % (item2[0], item2[1], group_name)
                    else:
                       str += ',{"To_Account":"%s", "Remark":"%s", "GroupName":["%s"], "AddSource":"AddSource_Type_SERVER"}' \
                                % (item2[0], item2[1], group_name)

        if str is None:
            return

        postdata = '{"From_Account":"%s", "AddFriendItem": [%s]}' % (from_account, str)

        Logger.Log('info', 'change_friend_group {0}'.format(postdata))

        return post(url, postdata)
