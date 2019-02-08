from django.contrib import admin
import common
from common.models import Shop, NationalId, ShopLicence

# Register your models here.

admin.site.register([Shop, ShopLicence])
admin.site.register(NationalId)