from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from .views import TestViewSet, Test2ViewSet
from .patch_views import PatchIMViewSet, PatchUserViewSet, PatchShopViewSet, PatchRedisViewSet
from .admin_viewset import AdminViewSet, NationalIdViewSet, ShopViewSet, PersionCashViewSet, FeedbackViewSet, \
    UserViewSet, MarketServerViewSet
from .im_update_view import IMViewSet


# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'zyftests', TestViewSet)
router.register(r'zyftests2', Test2ViewSet)
router.register(r'patch/im', PatchIMViewSet)
router.register(r'patch/user', PatchUserViewSet)
router.register(r'patch/shop', PatchShopViewSet)
router.register(r'patch/redis', PatchRedisViewSet)
router.register(r'admin', AdminViewSet)
router.register(r'nationid', NationalIdViewSet)
router.register(r'shop', ShopViewSet)
router.register(r'person_cashrecord', PersionCashViewSet)
router.register(r'feedback', FeedbackViewSet)
router.register(r'user', UserViewSet)
router.register(r'im', IMViewSet)
router.register(r'market_server', MarketServerViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
]