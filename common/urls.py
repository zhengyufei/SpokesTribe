from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter, DefaultRouter

from .views import obtain_auth_token, UserCreateViewSet, FindPasswordViewSet, UserNormalInfoViewSet,\
    UserNationalIdViewSet, ShopTypeViewSet, FeedbackViewSet, SmsVerifyViewSet, WeixinViewSet, QQViewSet, \
    WeiboViewSet, ZhifubaoViewSet, SettingViewSet, AboutViewSet

from .pay_callback_viewset import PayCallbackViewSet

# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'^register', UserCreateViewSet)
router.register(r'^find_password', FindPasswordViewSet)
router.register(r'^normal_info', UserNormalInfoViewSet)
router.register(r'^important_info', UserNationalIdViewSet)
router.register(r'^shop_type', ShopTypeViewSet)
router.register(r'^feedback', FeedbackViewSet)
router.register(r'^paycallback', PayCallbackViewSet)
router.register(r'^weixin', WeixinViewSet)
router.register(r'^qq', QQViewSet)
router.register(r'^weibo', WeiboViewSet)
router.register(r'^zhifubao', ZhifubaoViewSet)
router.register(r'^setting', SettingViewSet)
router.register(r'^about', AboutViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^token/', obtain_auth_token),
]

