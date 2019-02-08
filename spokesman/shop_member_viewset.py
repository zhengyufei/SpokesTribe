from django.db.models import Q
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
import decimal
from dateutil.relativedelta import relativedelta
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl
from RedisIF.shop import Shop as redis_shop
from common.models import Shop, ShopMemberCard, \
    Trade, TradeMemberProfile, ShopMember, ShopMemberRecharge, ShopMemberRechargeSnap, \
    ShopMemberRechargeTime, ShopMemberRechargeCount, ShopMemberRechargeTimeSnap, ShopMemberRechargeCountSnap
from .serializers import ShopMemberCardSerializer, ShopMemberRechargeSerializer, \
    TradeResponseSerializer, ShopMemberListSerializer, ShopMemberSerializer, \
    ShopMemberRechargeAllSerializer, ShopMemberRechargeTimeSerializer, ShopMemberRechargeCountSerializer


class ShopMemberCardViewSet(mixins.RetrieveModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = ShopMemberCard.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberCardSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberCard.objects.filter(shop_id=kwargs['pk_shop']).order_by('level')
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @list_route(methods=['get'])
    def list2(self, request, *args, **kwargs):
        try:
            shop_member = ShopMember.objects.get(shop_id=kwargs['pk_shop'], user=request.user)
        except ShopMember.DoesNotExist:
            raise ValidationDict211Error('error')
        serializer_mine = self.serializer_class(shop_member.member_card, context=self.get_serializer_context())
        queryset = ShopMemberCard.objects.filter(
            Q(shop_id=kwargs['pk_shop']) & ~Q(pk=shop_member.member_card.pk)).order_by('level')
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'mine': serializer_mine.data, 'other': serializer.data})

class AbstractShopMemberRechargeViewSet(mixins.RetrieveModelMixin,
                                mixins.ListModelMixin,
                                viewsets.GenericViewSet):
    def list(self, request, *args, **kwargs):
        filter = Q(shop_id=kwargs['pk_shop']) & Q(status='valid')

        if 'member_card' in request.query_params:
            filter &= Q(member_card=request.query_params['member_card'])

        queryset = self.class_name.objects.filter(filter)
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def recharge(self, request, pk_shop, pk=None):
        trade = self.recharge2(request, pk_shop, pk)

        serializer = TradeResponseSerializer({'id': trade.trade_number, 'price': trade.trade_price,
                                              'ico': GetAbsoluteImageUrl(request, trade.shop.ico_thumbnail)})
        return Response(serializer.data)

class ShopMemberRechargeViewSet(AbstractShopMemberRechargeViewSet):
    queryset = ShopMemberRecharge.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberRechargeSerializer

    def __init__(self, **kwargs):
        self.class_name = ShopMemberRecharge

        super(ShopMemberRechargeViewSet, self).__init__(**kwargs)

    def recharge2(self, request, pk_shop, pk=None):
        instance = self.get_object()
        shop = Shop.objects.get(pk=pk_shop)
        n_charge_ratio = int(redis_shop.get_charge_ratio(shop.id))
        charge_ratio = decimal.Decimal(n_charge_ratio / 10000)

        trade = Trade.objects.create(profile_type='member', shop=shop, buyer=request.user, spokesman=shop.seller,
                                     total_fee=instance.recharge + instance.gift, trade_price=instance.recharge)

        try:
            member = ShopMember.objects.get(shop=shop, user=request.user)
            after = member.loose_change + instance.recharge + instance.gift
        except ShopMember.DoesNotExist:
            after = instance.recharge + instance.gift

        dict_ectype = ShopMemberRechargeSnap.set(instance, after)
        snap = ShopMemberRechargeSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=instance.recharge, discount_reduce=instance.gift,
                                          shop_earning=instance.recharge * (1 - charge_ratio), recharge=snap)

        return trade

class ShopMemberRechargeTimeViewSet(AbstractShopMemberRechargeViewSet):
    queryset = ShopMemberRechargeTime.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberRechargeTimeSerializer

    def __init__(self, **kwargs):
        self.class_name = ShopMemberRechargeTime

        super(ShopMemberRechargeTimeViewSet, self).__init__(**kwargs)

    def recharge2(self, request, pk_shop, pk=None):
        instance = self.get_object()
        shop = Shop.objects.get(pk=pk_shop)
        n_charge_ratio = int(redis_shop.get_charge_ratio(shop.id))
        charge_ratio = decimal.Decimal(n_charge_ratio / 10000)

        trade = Trade.objects.create(profile_type='member', shop=shop, buyer=request.user, spokesman=shop.seller,
                                     total_fee=instance.recharge, trade_price=instance.recharge)

        try:
            member = ShopMember.objects.get(shop=shop, user=request.user)
            for item in member.time_set:
                if instance.service == item.service:
                    item.expire_time += relativedelta(months=instance.month)
                    after = item.expire_time
                    break
            else:
                after = instance.month
        except ShopMember.DoesNotExist:
            after = instance.month

        dict_ectype = ShopMemberRechargeTimeSnap.set(instance, after)
        snap = ShopMemberRechargeTimeSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=instance.recharge, discount_reduce=instance.gift,
                                          shop_earning=instance.recharge * (1 - charge_ratio), recharge_time=snap)

        return trade

class ShopMemberRechargeCountViewSet(AbstractShopMemberRechargeViewSet):
    queryset = ShopMemberRechargeCount.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberRechargeCountSerializer

    def __init__(self, **kwargs):
        self.class_name = ShopMemberRechargeTime

        super(ShopMemberRechargeCountViewSet, self).__init__(**kwargs)

    def recharge2(self, request, pk_shop, pk=None):
        instance = self.get_object()
        shop = Shop.objects.get(pk=pk_shop)
        n_charge_ratio = int(redis_shop.get_charge_ratio(shop.id))
        charge_ratio = decimal.Decimal(n_charge_ratio / 10000)

        trade = Trade.objects.create(profile_type='member', shop=shop, buyer=request.user, spokesman=shop.seller,
                                     total_fee=instance.recharge, trade_price=instance.recharge)

        try:
            member = ShopMember.objects.get(shop=shop, user=request.user)
            for item in member.count_set:
                if instance.service == item.service:
                    item.count += instance.count
                    after = item.count
                    break
            else:
                after = instance.count
        except ShopMember.DoesNotExist:
            after = instance.count

        dict_ectype = ShopMemberRechargeCountSnap.set(instance, after)
        snap = ShopMemberRechargeCountSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=instance.recharge, discount_reduce=instance.gift,
                                          shop_earning=instance.recharge * (1 - charge_ratio), recharge_count=snap)

        return trade

class ShopMemberRechargeAllViewSet(mixins.ListModelMixin,
                                   viewsets.GenericViewSet):
    queryset = ShopMemberRecharge.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberRechargeAllSerializer

    def list(self, request, *args, **kwargs):
        queryset = []

        queryset_save = ShopMemberRecharge.objects.filter(shop_id=kwargs['pk_shop'])

        for item in queryset_save:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, '储值',
                           str(item.gift), 'gift')
            queryset.append(serializer)

        queryset_time = ShopMemberRechargeTime.objects.filter(shop_id=kwargs['pk_shop'])

        for item in queryset_time:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, item.service.name,
                           str(item.month), 'time')
            queryset.append(serializer)

        queryset_count = ShopMemberRechargeCount.objects.filter(shop_id=kwargs['pk_shop'])

        for item in queryset_count:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, item.service.name,
                           str(item.count), 'count')
            queryset.append(serializer)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})


class ShopMemberViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = ShopMemberRecharge.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMember.objects.filter(user=request.user)

        for item in queryset:
            item.shop_id = item.shop.id
            item.shop_name = item.shop.name
            item.image = GetAbsoluteImageUrl(request, item.member_card.image)
            item.card_name = item.member_card.name
            item.number = str(item.id)

        serializer = ShopMemberListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = ShopMember.objects.get(user=request.user, shop_id=kwargs['pk'])

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)