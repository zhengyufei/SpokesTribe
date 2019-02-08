from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from .views import CardPackageViewSet, ShopMemberViewSet, Flyer2UserViewSet


# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'^card_package', CardPackageViewSet)
router.register(r'^card_package/shop_member', ShopMemberViewSet)
router.register(r'^card_package/flyer', Flyer2UserViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]