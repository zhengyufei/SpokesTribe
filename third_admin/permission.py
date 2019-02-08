from rest_framework.permissions import BasePermission

from MyAbstract.exceptions import ValidationDict211Error
from common.models import MarketServer


class IsThirdAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.marketserveremployeeship_set.count() > 0

class IsThirdAdminShopUser(BasePermission):
    def has_permission(self, request, view):
        pk_shop = view.kwargs['pk_shop']
        temp =  request.user.marketserveremployeeship_set
        return request.user and temp.count() > 0 \
               and temp.all()[0].group.server.shops.filter(pk=pk_shop).exists()

def third_admin_write(f):
    def wrapped_f(obj, request, *args, **kwargs):
        temp = request.user.marketserveremployeeship_set

        if temp.count() == 0 or temp.all()[0].group.level < 0:
            raise ValidationDict211Error('没有权限')

        return f(obj, request, *args, **kwargs)
    return wrapped_f

def third_admin_shop_write(f):
    def wrapped_f(obj, request, *args, **kwargs):
        temp = request.user.marketserveremployeeship_set

        if temp.count() == 0 or temp.all()[0].group.level < 0\
                or not temp.all()[0].group.server.shops.filter(pk=kwargs['pk_shop']).exists():
            raise ValidationDict211Error('没有权限')

        return f(obj, request, *args, **kwargs)
    return wrapped_f
