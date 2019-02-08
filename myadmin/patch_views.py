from rest_framework import parsers, renderers, viewsets, permissions, generics, mixins, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from django.db import connection,transaction
import json
from common.models import MyUser, FriendGroup, Shop, ShopActivity, ShopDiscount, Wallet, ShopSpokeGroup
from common.serializers import EmptySerializer
from .serializers import ShopLocationSerializer, ShopRatioSerializer
from IM.IM import IM as im
from RedisIF.RedisIF import RedisIF
from RedisIF.shop import Shop as redis_shop
from MyAbstract.funtions import GetAbsoluteImageUrl


class PatchViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

class PatchIMViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def batch_add(self, request, *args, **kwargs):
        return Response(im.batch_add())

    @list_route(methods=['get'])
    def all_modify_allow_type(self, request, *args, **kwargs):
        queryset = MyUser.objects.all()

        for query in queryset:
            im.modify_allow_type(query.id)

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def all_update_info(self, request, *args, **kwargs):
        queryset = MyUser.objects.all()

        for query in queryset:
            im.modify_nick(query.id, query.nick_name)
            major = query.spoke_profile.major_shop.type.name if query.spoke_profile.major_shop else ''
            im.modify_major_spokes(query.id, major=major)
            im.modify_ico(query.id, GetAbsoluteImageUrl(request, query.ico_thumbnail))

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def get_test_info(self, request, *args, **kwargs):
        return Response(im.get_userinfo('13408544338'))

class PatchUserViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def wallet(self, request, *args, **kwargs):
        query = MyUser.objects.all()

        for user in query:
            if not Wallet.objects.filter(user=user).exists():
                Wallet(user=user).save()

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def friend_group(self, request, *args, **kwargs):
        query = MyUser.objects.all()

        for user in query:
            if not FriendGroup.objects.filter(user=user, type=1).exists():
                FriendGroup(user=user, type=1, name='客人').save()

            if not FriendGroup.objects.filter(user=user, type=2).exists():
                FriendGroup(user=user, type=2, name='挚友').save()

            if not FriendGroup.objects.filter(user=user, type=3).exists():
                FriendGroup(user=user, type=3, name='好友').save()

        return Response({'result': 'OK'})

class PatchShopViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def activity(self, request, *args, **kwargs):
        query = Shop.objects.all()

        for shop in query:
            if not ShopActivity.objects.filter(shop=shop).exists():
                ShopActivity(shop=shop, is_valid=0, type=1, discount=100, full_price=100, reduce_price=100).save()

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def discount(self, request, *args, **kwargs):
        query = Shop.objects.all()

        for shop in query:
            if not ShopDiscount.objects.filter(shop=shop).exists():
                ShopDiscount(shop=shop, is_valid=True, type=1, discount=100, full_price=100, reduce_price=100).save()

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def spokes_group(self, request, *args, **kwargs):
        sql = "SELECT A.shop_id, B.id FROM common_shopspoke AS A " \
              "LEFT JOIN common_friendgroup AS B ON A.spokesman_id = B.user_id WHERE B.type = 3"

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        for obj in fetchall:
            try:
                ShopSpokeGroup.objects.create(shop_id=obj[0], group_id=obj[1], discount=80)
            except:
                pass

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    def location(self, request, pk=None):
        serializer = ShopLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']
        Shop.objects.filter(pk=pk).update(latitude=latitude, longitude=longitude)
        RedisIF.r.geoadd('ShopGeo', longitude, latitude, pk)

        return Response({''})

    @detail_route(methods=['post'])
    def charge_ratio(self, request, pk=None):
        serializer = ShopRatioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ratio = serializer.validated_data['ratio']
        Shop.objects.filter(pk=pk).update(charge_ratio=ratio)
        redis_shop.set_charge_ratio(pk, ratio)

        return Response({''})

    @detail_route(methods=['post'])
    def brokerage_ratio(self, request, pk=None):
        serializer = ShopRatioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ratio = serializer.validated_data['ratio']
        Shop.objects.filter(pk=pk).update(brokerage_ratio=ratio)
        redis_shop.set_brokerage_ratio(pk, ratio)

        return Response({''})

class PatchRedisViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def init(self, request, *args, **kwargs):
        for shop in Shop.objects.all():
            RedisIF.r.geoadd('ShopGeo', shop.longitude, shop.latitude, shop.id)
            redis_shop.set_charge_ratio(shop.id, shop.charge_ratio)
            redis_shop.set_brokerage_ratio(shop.id, shop.brokerage_ratio)

        return Response('')

    @list_route(methods=['get'])
    def geoadd(self, request, *args, **kwargs):
        for shop in Shop.objects.all():
            RedisIF.r.geoadd('ShopGeo', shop.longitude, shop.latitude, shop.id)

        return Response('')

    @list_route(methods=['get'])
    def georemove(self, request, *args, **kwargs):
        query = Shop.objects.all()

        for shop in query:
            RedisIF.r.zrem('ShopGeo', shop.id)

        return Response('')

    @list_route(methods=['get'])
    def georadius(self, request, *args, **kwargs):
        return Response(RedisIF.r.georadius('ShopGeo', 124.91, 28.37, 30000, unit="m", withdist=True))

    @list_route(methods=['get'])
    def shop_charge_ratio(self, request, *args, **kwargs):
        for shop in Shop.objects.all():
            redis_shop.set_charge_ratio(shop.id, shop.charge_ratio)

        return Response('')

    @list_route(methods=['get'])
    def shop_brokerage_ratio(self, request, *args, **kwargs):
        for shop in Shop.objects.all():
            redis_shop.set_brokerage_ratio(shop.id, shop.brokerage_ratio)

        return Response('')