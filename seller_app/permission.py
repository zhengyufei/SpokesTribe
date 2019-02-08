from django.db.models import Q
from rest_framework.permissions import BasePermission

from MyAbstract.exceptions import ValidationDict211Error
from common.models import Shop, ShopPhoto, ShopSpokeRequest, ShopSpoke, ShopWallet, ShopMemberCard, ShopMember, \
    ShopMemberRecharge, ShopMemberRechargeTime, ShopMemberRechargeCount


class IsSeller(BasePermission):
    def has_permission(self, request, view):
        if not Shop.objects.filter(id=view.kwargs['pk_shop'], seller=request.user).exists():
            raise ValidationDict211Error('没有所有者权限')

        return True

    def has_object_permission(self, request, view, obj=None):
        if not Shop.objects.filter(id=view.kwargs['pk_shop'], seller=request.user).exists():
            raise ValidationDict211Error('没有所有者权限')

        return True

class IsManager(BasePermission):
    def has_permission(self, request, view):
        if 'pk_shop' not in view.kwargs and 'pk' not in view.kwargs:
            return True

        pk = view.kwargs['pk_shop'] if 'pk_shop' in view.kwargs else view.kwargs['pk']
        if not Shop.objects.filter(pk=pk, managers=request.user).exists():
            raise ValidationDict211Error('没有管理权限')

        return True

    def has_object_permission(self, request, view, obj=None):
        pk = view.kwargs['pk_shop'] if 'pk_shop' in view.kwargs else view.kwargs['pk']
        if not Shop.objects.filter(pk=pk, managers=request.user).exists():
            raise ValidationDict211Error('没有管理权限')

        return True

def shop_operate(f):
    def wrapped_f(obj, request, *args, **kwargs):
        pk = kwargs['pk_shop'] if 'pk_shop' in kwargs else kwargs['pk']

        try:
            shop = Shop.objects.get(pk=pk)
        except Shop.DoesNotExist:
            raise ValidationDict211Error('店铺不存在')

        if not shop.state is 4:
            raise ValidationDict211Error('店铺未在运营状态')
        return f(obj, request, *args, **kwargs)
    return wrapped_f

def shop_manage(f):
    def wrapped_f(obj, request, *args, **kwargs):
        pk = kwargs['pk_shop'] if 'pk_shop' in kwargs else kwargs['pk']

        if not Shop.objects.filter(pk=pk, managers=request.user).exists():
            raise ValidationDict211Error('没有访问权限')
        return f(obj, request, *args, **kwargs)
    return wrapped_f

def manage(f, class_name):
    def wrapped_f(obj, request, *args, **kwargs):
        pk_shop = kwargs['pk_shop']
        pk = kwargs['pk']

        if not class_name.objects.filter(pk=pk, shop_id=pk_shop, shop__managers=request.user).exists():
            raise ValidationDict211Error('没有访问权限')

        return f(obj, request, *args, **kwargs)

    return wrapped_f

def shop_photo_manage_only(f):
    return manage(f, ShopPhoto)

def shop_spokes_request_manage_only(f):
    def wrapped_f(obj, request, *args, **kwargs):
        pk_shop = kwargs['pk_shop']
        pk = kwargs['pk']

        if not ShopSpokeRequest.objects.filter(resume_id=pk, shop_id=pk_shop, shop__managers=request.user).exists():
            raise ValidationDict211Error('没有访问权限')

        return f(obj, request, *args, **kwargs)

    return wrapped_f

def shop_spokes_manage_only(f):
    return manage(f, ShopSpoke)

def shop_member_card_manage_only(f):
    return manage(f, ShopMemberCard)

def shop_member_recharge_manage_only(f):
    return manage(f, ShopMemberRecharge)

def shop_member_recharge_time_manage_only(f):
    return manage(f, ShopMemberRechargeTime)

def shop_member_recharge_count_manage_only(f):
    return manage(f, ShopMemberRechargeCount)

def shop_member_manage_only(f):
    return manage(f, ShopMember)

