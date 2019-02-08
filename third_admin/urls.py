from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from .views import ShopViewSet, ShopPhotoViewSet


# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'shop', ShopViewSet)
router.register(r'shop/(?P<pk_shop>[0-9]+)/photo', ShopPhotoViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]