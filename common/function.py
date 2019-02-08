import datetime
import re
from django.db.models import Q
from django.db import connection, IntegrityError
from MyAbstract.exceptions import ValidationDict211Error
from math import ceil, floor
from SpokesTribe.settings import BROTHER_RATIO1, BROTHER_RATIO2

from .models import Wallet, FriendGroup, MyUserSpokeProfile, MyUserSettingProfile, Festival, ShopSpoke, \
    MyUserSellerSettingProfile
import SpokesTribe.settings as settings
from IM.IM import IM as im
from MyAbstract.funtions import GetFixedImageUrl, GetAbsoluteImageUrl
from rest_framework.response import Response


def phonecheck(s):
    # 检测号码是否长度是否合法。
    if len(s) != 11:
        return [False, '长度不对', 'The length of phonenum is 11.']
    else:
        # 检测输入的号码是否全部是数字。
        if s.isdigit():
                return [True]
        else:
            return False, ['手机号格式不正确', 'The phone num is made up of digits.']


def isidcard(id_number):
    area_dict = {11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古", 21: "辽宁", 22: "吉林", 23: "黑龙江", 31: "上海", 32: "江苏",
                 33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东", 41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西",
                 46: "海南", 50: "重庆", 51: "四川", 52: "贵州", 53: "云南", 54: "西藏", 61: "陕西", 62: "甘肃", 63: "青海", 64: "新疆",
                 71: "台湾", 81: "香港", 82: "澳门", 91: "外国"}
    id_code_list = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_code_list = [1, 0, 'X', 9, 8, 7, 6, 5, 4, 3, 2]
    if len(id_number) != 18:
        return False, "Length error"
    if not re.match(r"^\d{17}(\d|X|x)$", id_number):
        return False, "Format error"
    if int(id_number[0:2]) not in area_dict:
        return False, "Area code error"
    try:
        datetime.date(int(id_number[6:10]), int(id_number[10:12]), int(id_number[12:14]))
    except ValueError as ve:
        return False, "Datetime error: {0}".format(ve)

    if str(check_code_list[sum([a * b for a, b in zip(id_code_list, [int(a) for a in id_number[0:-1]])]) % 11]) != id_number.upper()[-1]:
        return False, "Check code error"

    return (True,)

def spoker_type(shop_id, spoker_id):
    try:
        temp = ShopSpoke.objects.get(Q(shop_id=shop_id) & (Q(spokesman_id=spoker_id) | Q(member__user_id=spoker_id)))
    except:
        return None

    if 'member' == temp.type and temp.member.loose_change > 0:
        return temp.type
    elif 'normal' == temp.type:
        return temp.type
    else:
        return None

def discount_describe_mine(is_valid, type=1, discount=100, full_price=100, reduce_price=0, **kwargs):
    if not is_valid \
            or (1 == type and discount in (None, 100)) \
            or (2 == type and reduce_price in (None, 0)):
        return None
    elif 1 == type:
        return "独享优惠{0}折".format(discount / 10)
    elif 2 == type:
        return "独享优惠满{0}减{1}元".format(full_price, reduce_price)

def discount_describe_brother(is_valid, type=1, discount=100, full_price=100, reduce_price=0, **kwargs):
    if not is_valid:
        return None, None
    elif ((1 == type and (discount in (None, 100))) or (2 == type and (reduce_price in (None, 0)))):
        return None, None
    elif 1 == type:
        temp = (ceil(discount * BROTHER_RATIO1) + BROTHER_RATIO2)
        return temp, "挚友独享优惠{0}折".format(temp / 10)
    elif 2 == type:
        temp = floor(reduce_price * BROTHER_RATIO1)
        return temp, "挚友独享优惠满{0}减{1}元".format(full_price, temp)
    else:
        return None, None

def discount_describe_friend(group_type, is_valid, type=1, discount=100, full_price=100, reduce_price=0, friend_discount=None):
    if not is_valid or 1 == group_type:
        return None, None
    elif 2 == group_type and ((1 == type and (discount in (None, 100))) or (2 == type and (reduce_price in (None, 0)))):
        return None, None
    elif group_type not in (1, 2) and (not friend_discount
        or (1 == type and (discount in (None, 100) or friend_discount in (None, 100) or friend_discount <= discount))
        or (2 == type and (reduce_price in (None, 0) or friend_discount in (None, 100) or friend_discount >= reduce_price))):
        return None, None
    elif 1 == type:
        if 2 == group_type:
            temp = (ceil(discount * BROTHER_RATIO1) + BROTHER_RATIO2)
            return temp, "挚友独享优惠{0}折".format(temp / 10)
        else:
            temp = friend_discount
            return temp, "好友独享优惠{0}折".format(temp / 10)
    elif 2 == type:
        if 2 == group_type:
            temp = floor(reduce_price * BROTHER_RATIO1)
            return temp, "挚友独享优惠满{0}减{1}元".format(full_price, temp)
        else:
            temp = friend_discount
            return temp, "好友独享优惠满{0}减{1}元".format(full_price, temp)
    else:
        return None, None

def register_profile(request, user):
    MyUserSpokeProfile.objects.create(user=user)
    MyUserSettingProfile.objects.create(user=user)
    MyUserSellerSettingProfile.objects.create(user=user)
    Wallet.objects.create(user=user)
    FriendGroup.objects.create(user=user, type=1, name='客人')
    FriendGroup.objects.create(user=user, type=2, name='挚友')
    FriendGroup.objects.create(user=user, type=3, name='好友')

    if settings.IM_ONLINE:
        im.add(user.id, user.nick_name, GetFixedImageUrl(request, user.ico_thumbnail))
        im.modify_allow_type(user.id)

def is_festival(date=datetime.datetime.now()):
    return date.weekday() in (5, 6) or Festival.objects.filter(date=date).exists()

def response_page(obj, serializer_class, queryset):
    page = obj.paginate_queryset(queryset)

    if page is not None:
        serializer = serializer_class(page, many=True, context=obj.get_serializer_context())
        return obj.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True, context=obj.get_serializer_context())
    return Response(serializer.data)

def response_list(obj, serializer_class, queryset):
    serializer = serializer_class(queryset, many=True, context=obj.get_serializer_context())
    return Response({'results': serializer.data})

