import datetime
from django.db import connection
from django.db.models import F, Q
from rest_framework import parsers, renderers, viewsets, permissions, generics, mixins, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from RedisIF.shop import Shop as redis_shop
from common.models import MyUser, Shop, ShopPhoto, MarketServer, MarketServerShopShip, MarketServerEmployeeShip, \
    MarketServerGroup
from common.serializers import ShopPhotoSerializer, ShopPhotoAddListSerializer, DelIDsSerializer
from .serializers import ShopListSerializer, ShopSerializer, ShopCreateSerializer, ShopFilterSerializer
from .permission import IsThirdAdminUser, IsThirdAdminShopUser, third_admin_write, third_admin_shop_write


# Create your views here.
class ShopViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsThirdAdminUser]
    serializer_class = ShopSerializer

    def list(self, request, *args, **kwargs):
        serializer = ShopFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        ship = MarketServerEmployeeShip.objects.filter(user=request.user)[0]
        filter = Q(marketserver=ship.group.server)

        if 'name' in serializer.validated_data.keys():
            name = serializer.validated_data['name']
            filter &= Q(name__contains=name)

        if 'staff_name' in serializer.validated_data.keys():
            staff_name = serializer.validated_data['staff_name']
            filter &= Q(staff_name=staff_name)

        if 'begin_time' in serializer.validated_data.keys():
            begin_time = serializer.validated_data['begin_time']
            end_time = serializer.validated_data['end_time']
            filter &= Q(join_time__gte=begin_time) & Q(join_time__lt=end_time)

        queryset = Shop.objects.filter(filter)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ShopListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ShopListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @third_admin_write
    def create(self, request, *args, **kwargs):
        serializer = ShopCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ship = MarketServerEmployeeShip.objects.filter(group__level=0, user=request.user)[0]

        serializer.request = request
        serializer.save(server=ship.group.server, staff_name=ship.name)

        return Response({'detail': 'OK'})


class ShopPhotoViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopPhoto.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsThirdAdminShopUser]
    serializer_class = ShopPhotoSerializer

    def list(self, request, *args, **kwargs):
        ship = MarketServerEmployeeShip.objects.filter(user=request.user)[0]
        queryset = ShopPhoto.objects.filter(shop__marketserver=ship.group.server)
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())

        return Response({'results':serializer.data})

    @third_admin_shop_write
    def destroy(self, request, *args, **kwargs):
        return super(ShopPhotoViewSet, self).destroy(request, *args, **kwargs)

    @list_route(methods=['post'])
    @third_admin_shop_write
    def add_photos(self, request, *args, **kwargs):
        serializer = ShopPhotoAddListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['shop'] = Shop.objects.get(pk=kwargs['pk_shop'])
        serializer.save(serializer.validated_data)
        return Response({'detail': 'OK'})

    @list_route(methods=['post'])
    @third_admin_shop_write
    def del_photos(self, request, *args, **kwargs):
        serializer = DelIDsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ShopPhoto.objects.filter(shop_id=kwargs['pk_shop'], pk__in=serializer.validated_data['ids']).delete()
        return Response({'detail': 'OK'})


class GroupViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = MarketServerGroup.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsThirdAdminUser]
    serializer_class = ShopSerializer

    def list(self, request, *args, **kwargs):
        ship = MarketServerGroup.objects.filter(level=0, user=request.user)[0]
        queryset = Shop.objects.filter(marketserver=ship.group.server)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ShopListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ShopListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @third_admin_write
    def create(self, request, *args, **kwargs):
        serializer = ShopCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ship = MarketServerEmployeeShip.objects.filter(group__level=0, user=request.user)[0]

        serializer.request = request
        serializer.save(server=ship.group.server, staff_name=ship.name)

        return Response({'detail': 'OK'})
