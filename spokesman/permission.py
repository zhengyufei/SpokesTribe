from rest_framework.permissions import BasePermission
from django.db.models import Q

from MyAbstract.exceptions import ValidationDict211Error
from common.models import ShopSpoke, Wallet

import datetime


class HasPayPassword(BasePermission):
    def has_permission(self, request, view):
        if not Wallet.objects.get(user=request.user).has_usable_password():
            raise ValidationDict211Error('未设置支付密码')

        return True

    #def has_object_permission(self, request, view, obj=None):
    #    return request.method in permissions.SAFE_METHODS

def shop_spokes_only(f):
    def wrapped_f(obj, request, *args, **kwargs):
        pk = kwargs['pk_shop'] if 'pk_shop' in kwargs else kwargs['pk']

        if not ShopSpoke.objects.filter(Q(shop_id=pk) & (Q(spokesman=request.user) | Q(member__user=request.user))).exists():
            raise ValidationDict211Error('没有访问权限')
        return f(obj, request, *args, **kwargs)
    return wrapped_f

def combo_time(f):
    def wrapped_f(obj, request, *args, **kwargs):
        now = datetime.datetime.now()
        time1 = now.replace(hour=23, minute=55, second=0, microsecond=0)
        time2 = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if now > time1 or now < time2:
            raise ValidationDict211Error('暂时不能购买套餐')

        return f(obj, request, *args, **kwargs)
    return wrapped_f