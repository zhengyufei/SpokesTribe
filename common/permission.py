from rest_framework.permissions import BasePermission

from MyAbstract.exceptions import ValidationDict211Error
from .models import NationalId, ShopCombo


class HasNationalId(BasePermission):
    def has_permission(self, request, view):
        if not NationalId.objects.filter(user=request.user).exists():
            raise ValidationDict211Error('未实名制')

        return True

class ShopComboOnline(BasePermission):
    def has_permission(self, request, view):
        try:
            return ShopCombo.objects.get(pk=view.kwargs['pk']).is_online()
        except:
            return False

def per_phone_number(f):
    def wrapped_f(obj, request, *args, **kwargs):
        if not request.user.phone_number:
            raise ValidationDict211Error('未绑定手机号')

        return f(obj, request, *args, **kwargs)
    return wrapped_f
