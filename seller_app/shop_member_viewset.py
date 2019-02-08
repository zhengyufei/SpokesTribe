# Create your views here.
import datetime
import decimal, copy
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from django.db import connection
from django.db.models import Q
from rest_framework import status
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from APNS import apns, apns_push
from MyAbstract.exceptions import ValidationDict211Error
from common.models import create_trade_number, Trade, TradeDiscountProfile, TradeRecord, \
    ShopMemberCard, ShopMember, ShopMemberRecharge, ShopMemberService, ShopMemberRechargeTime, ShopMemberRechargeCount, \
    TradeMemberProfile, TradePay, ShopMemberRechargeSnap, ShopMemberRechargeTimeSnap, ShopMemberRechargeCountSnap, \
    ShopMemberTimeProfile, ShopMemberDelSnap, ShopSpoke, ShopSpokeGroup
from common.function import response_list, response_page

from .permission import shop_member_card_manage_only, shop_member_manage_only, \
    shop_member_recharge_manage_only, shop_member_recharge_time_manage_only, shop_member_recharge_count_manage_only

from .serializers import ShopMemberCardSerializer, ShopMemberSerializer, TradeMemberRechageSerializer, \
    ShopMemberRechargeSerializer, ShopMemberServiceSerializer, ShopMemberRechargeTimeSerializer, ShopMemberRechargeCountSerializer, \
    ShopMemberBatchSerializer, TradeMemberConsumeSerializer, TradeMemberRechageInputSerializer, \
    TimeFilterSerializer, \
    ShopMemberRechargeAllSerializer, TradeMemberRechageTimeInputSerializer, TradeMemberRechageCountInputSerializer, \
    TradeMemberConsumeTimeSerializer, TradeMemberConsumeCountSerializer

from .serializers import ShopMemberListAppSerializer, ShopMemberCardListSerializer, MemberRechargeHistoryAppSerializer, \
    MemberConsumeHistoryAppSerializer

from .permission import IsManager


class ShopMemberCardViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberCard.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberCardSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberCard.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user).order_by('level')

        return response_list(self, ShopMemberCardListSerializer, queryset)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    @shop_member_card_manage_only
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.recharge = instance.shopmemberrecharge_set.all()

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @shop_member_card_manage_only
    def update(self, request, *args, **kwargs):
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

    @shop_member_card_manage_only
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

class ShopMemberRechargeViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberRecharge.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberRechargeSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberRecharge.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['member_card'].shop_id != int(kwargs['pk_shop']):
            raise ValidationDict211Error('error')

        serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    @shop_member_recharge_manage_only
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @shop_member_recharge_manage_only
    def update(self, request, *args, **kwargs):
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

    @shop_member_recharge_manage_only
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

class ShopMemberServiceViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberService.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberServiceSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberService.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user, status='valid')
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = ShopMemberService.objects.get(shop_id=kwargs['pk_shop'], name=serializer.validated_data['name'])
            if service.status != 'valid':
                service.status = 'valid'
                service.save(update_fields=['status'])
        except:
            serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'valid':
            raise ValidationDict211Error('error')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        ShopMemberService.objects.filter(pk=kwargs['pk']).update(status='invalid')

        return Response({'detail': 'OK'})

class ShopMemberRechargeTimeViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberRechargeTime.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberRechargeTimeSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberRechargeTime.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['member_card'].shop_id != int(kwargs['pk_shop']):
            raise ValidationDict211Error('error')

        serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    @shop_member_recharge_time_manage_only
    def retrieve(self, request, *args, **kwargs):
        return super(ShopMemberRechargeTimeViewSet, self).retrieve(request, *args, **kwargs)

    @shop_member_recharge_time_manage_only
    def update(self, request, *args, **kwargs):
        return super(ShopMemberRechargeTimeViewSet, self).update(request, *args, **kwargs)

    @shop_member_recharge_time_manage_only
    def partial_update(self, request, *args, **kwargs):
        return super(ShopMemberRechargeTimeViewSet, self).partial_update(request, *args, **kwargs)

    @shop_member_recharge_time_manage_only
    def destroy(self, request, *args, **kwargs):
        return super(ShopMemberRechargeTimeViewSet, self).destroy(request, *args, **kwargs)

class ShopMemberRechargeCountViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberRechargeCount.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberRechargeCountSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMemberRechargeCount.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['member_card'].shop_id != int(kwargs['pk_shop']):
            raise ValidationDict211Error('error')

        serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    @shop_member_recharge_count_manage_only
    def retrieve(self, request, *args, **kwargs):
        return super(ShopMemberRechargeCountViewSet, self).retrieve(request, *args, **kwargs)

    @shop_member_recharge_count_manage_only
    def update(self, request, *args, **kwargs):
        return super(ShopMemberRechargeCountViewSet, self).update(request, *args, **kwargs)

    @shop_member_recharge_count_manage_only
    def partial_update(self, request, *args, **kwargs):
        return super(ShopMemberRechargeCountViewSet, self).partial_update(request, *args, **kwargs)

    @shop_member_recharge_count_manage_only
    def destroy(self, request, *args, **kwargs):
        return super(ShopMemberRechargeCountViewSet, self).destroy(request, *args, **kwargs)

class ShopMemberRechargeAllViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMemberRechargeCount.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberRechargeAllSerializer

    def list(self, request, *args, **kwargs):
        queryset = []

        queryset_save = ShopMemberRecharge.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)

        for item in queryset_save:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, '储值',
                                str(item.gift), 'gift')
            queryset.append(serializer)

        queryset_time = ShopMemberRechargeTime.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)

        for item in queryset_time:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, item.service.name,
                                str(item.month), 'time')
            queryset.append(serializer)

        queryset_count = ShopMemberRechargeCount.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user)

        for item in queryset_count:
            serializer = self.serializer_class()
            serializer.set(item.id, item.member_card_id, item.member_card.name, item.recharge, item.service.name,
                                str(item.count), 'count')
            queryset.append(serializer)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class ShopMemberViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.ListModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopMember.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopMemberSerializer

    def list(self, request, *args, **kwargs):
        filter = Q(shop_id=kwargs['pk_shop']) & Q(shop__managers=request.user)

        if 'name' in request.query_params:
            name = request.query_params['name']
            filter &= (Q(user__phone_number=name) | Q(name__contains=name))

        queryset = ShopMember.objects.filter(filter)

        return response_page(self, ShopMemberListAppSerializer, queryset)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=request, shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    @list_route(methods=['post'])
    def batch_create(self, request, *args, **kwargs):
        serializer = ShopMemberBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        failed = serializer.save(request=request, shop_id=kwargs['pk_shop'])

        return Response({'results': failed}, status=status.HTTP_201_CREATED)

    @shop_member_manage_only
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.ico = instance.user.ico
        instance.card = instance.member_card.name
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @shop_member_manage_only
    def update(self, request, *args, **kwargs):
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

    @shop_member_manage_only
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

    @shop_member_manage_only
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ShopSpoke.objects.filter(shop=instance.shop, member=instance).delete()
        ShopSpokeGroup.objects.filter(shop=instance.shop, group__user=instance.user).delete()
        dict_ectype = ShopMemberDelSnap.set(instance)
        ShopMemberDelSnap.objects.create(**dict_ectype)

        return mixins.DestroyModelMixin.destroy(self, request, *args, **kwargs)

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge(self, request, pk_shop, pk):
        serializer = TradeMemberRechageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recharge_id = serializer.validated_data['recharge_id']
        member = ShopMember.objects.get(pk=pk)
        user = member.user

        try:
            recharge = ShopMemberRecharge.objects.get(shop_id=pk_shop, pk=recharge_id)
        except ShopMemberRecharge.DoesNotExist:
            raise ValidationDict211Error('error')

        amount = recharge.recharge

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
             total_fee=amount + recharge.gift, trade_price=amount, has_pay=True)

        instance = self.get_object()
        instance.loose_change += (amount + recharge.gift)
        instance.save(update_fields=['loose_change'])

        dict_ectype = ShopMemberRechargeSnap.set(recharge, instance.loose_change)
        snap = ShopMemberRechargeSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=recharge.gift,
            shop_earning=amount, status='pay', recharge=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge_input(self, request, pk_shop, pk):
        serializer = TradeMemberRechageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ShopMember.objects.get(pk=pk)
        user = member.user
        amount = serializer.validated_data['amount']
        gift = serializer.validated_data['gift']

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
            total_fee=amount + gift, trade_price=amount, has_pay=True)

        instance = self.get_object()
        instance.loose_change += (amount + gift)
        instance.save(update_fields=['loose_change'])

        snap = ShopMemberRechargeSnap.objects.create(shop_id=pk_shop, member_card=member.member_card,
            name='offline', recharge=amount, gift=gift, after=instance.loose_change)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=gift,
            shop_earning=amount, status = 'pay', recharge=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge_time(self, request, pk_shop, pk):
        serializer = TradeMemberRechageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recharge_id = serializer.validated_data['recharge_id']
        member = ShopMember.objects.get(pk=pk)
        user = member.user

        try:
            recharge = ShopMemberRechargeTime.objects.get(shop_id=pk_shop, pk=recharge_id)
        except ShopMemberRechargeTime.DoesNotExist:
            raise ValidationDict211Error('error')

        amount = recharge.recharge

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
            total_fee=amount, trade_price=amount, has_pay=True)

        instance = self.get_object()
        for item in instance.time_set:
            if recharge.service == item.service:
                item.expire_time += relativedelta(months=recharge.month)
                item.save(update_fields=['expire_time'])
                after = item.expire_time

                break
        else:
            after = datetime.datetime.now() + relativedelta(months=instance.month)
            ShopMemberTimeProfile.objects.create(member=instance, service=recharge.service, expire_time=after)

        dict_ectype = ShopMemberRechargeTimeSnap.set(recharge, after)
        snap = ShopMemberRechargeTimeSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=recharge.gift,
            shop_earning=amount, status='pay', recharge_time=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge_time_input(self, request, pk_shop, pk):
        serializer = TradeMemberRechageTimeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ShopMember.objects.get(pk=pk)
        user = member.user
        amount = serializer.validated_data['amount']
        service_id = serializer.validated_data['service_id']
        month = serializer.validated_data['month']

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
            total_fee=amount, trade_price=amount, has_pay=True)

        instance = self.get_object()
        for item in instance.time_set:
            if service_id == item.service.id:
                item.expire_time += relativedelta(months=month)
                item.save(update_fields=['expire_time'])
                after = item.expire_time

                break
        else:
            after = datetime.datetime.now() + relativedelta(months=instance.month)
            ShopMemberTimeProfile.objects.create(member=instance, service_id=service_id, expire_time=after)

        snap = ShopMemberRechargeTimeSnap.objects.create(shop_id=pk_shop, member_card=member.member_card,
            name='offline', recharge=amount, service_id=service_id, month=month, after=after)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=0,
            shop_earning=amount, status='pay', recharge_time=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge_count(self, request, pk_shop, pk):
        serializer = TradeMemberRechageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recharge_id = serializer.validated_data['recharge_id']
        member = ShopMember.objects.get(pk=pk)
        user = member.user

        try:
            recharge = ShopMemberRechargeCount.objects.get(shop_id=pk_shop, pk=recharge_id)
        except ShopMemberRechargeCount.DoesNotExist:
            raise ValidationDict211Error('error')

        amount = recharge.recharge

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
            total_fee=amount, trade_price=amount, has_pay=True)

        instance = self.get_object()
        for item in instance.count_set:
            if recharge.service == item.service:
                item.count += recharge.count
                item.save(update_fields=['count'])
                after = item.count

                break
        else:
            after = recharge.count
            ShopMemberTimeProfile.objects.create(member=instance, service=recharge.service, count=after)

        dict_ectype = ShopMemberRechargeCountSnap.set(recharge, after)
        snap = ShopMemberRechargeCountSnap.objects.create(**dict_ectype)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=recharge.gift,
            shop_earning=amount, status='pay', recharge_count=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def recharge_count_input(self, request, pk_shop, pk):
        serializer = TradeMemberRechageCountInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = ShopMember.objects.get(pk=pk)
        user = member.user
        amount = serializer.validated_data['amount']
        service_id = serializer.validated_data['service_id']
        count = serializer.validated_data['count']

        trade = Trade.objects.create(profile_type='member', shop_id=pk_shop, buyer_id=user.id, spokesman=request.user,
            total_fee=amount, trade_price=amount, has_pay=True)

        instance = self.get_object()
        for item in instance.count_set:
            if service_id == item.service.id:
                item.count += count
                item.save(update_fields=['count'])
                after = item.count

                break
        else:
            after = count
            ShopMemberTimeProfile.objects.create(member=instance, service=service_id, count=after)

        snap = ShopMemberRechargeCountSnap.objects.create(shop_id=pk_shop, member_card=member.member_card,
            name='offline', recharge=amount, service_id=service_id, count=count, after=after)

        TradeMemberProfile.objects.create(trade=trade, trade_price=amount, discount_reduce=0,
            shop_earning=amount, status='pay', recharge_count=snap)

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='offline', is_seller=True,
            card_name=member.member_card.name)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_recharge(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def consume(self, request, pk_shop, pk):
        serializer = TradeMemberConsumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        user = ShopMember.objects.get(pk=pk).user

        instance = self.get_object()
        if instance.loose_change < amount:
            raise ValidationDict211Error('会员卡余额不足')

        instance.loose_change -= amount
        instance.save(update_fields=['loose_change'])

        trade = Trade.objects.create(profile_type='discount', shop_id=pk_shop, buyer=user, spokesman=request.user,
            total_fee=amount, trade_price=amount, has_pay=True)

        TradeDiscountProfile.objects.create(trade=trade, trade_price=amount, activity='', discount_price=0,
            constant_price=amount, activity_reduce=0, discount_reduce=0, shop_earning=0,
            pay_platform_expend=0, owner_earning=0, status='confirm', confirm_time=datetime.datetime.now())

        TradePay.objects.create(trade=trade, trade_price=amount, charge_ratio=0, pay_type='member', is_seller=True,
            remain=instance.loose_change)

        trade.set_settle_type()

        record = TradeRecord.objects.create(trade=trade, confirm=True)

        apns_push.handle_seller_member_consume(record)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def consume_time(self, request, pk_shop, pk):
        serializer = TradeMemberConsumeTimeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data['service_id']
        month = serializer.validated_data['month']
        user = ShopMember.objects.get(pk=pk).user

        instance = self.get_object()
        for item in instance.time_set:
            if item.service.id == service_id:
                if item.expire_time < timezone.now():
                    raise ValidationDict211Error('时效卡已过期')
                else:
                    break
        else:
            raise ValidationDict211Error('无时效卡')

        # TODO record time card
        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def consume_count(self, request, pk_shop, pk):
        serializer = TradeMemberConsumeCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data['service_id']
        count = serializer.validated_data['count']
        user = ShopMember.objects.get(pk=pk).user

        instance = self.get_object()
        for item in instance.count_set:
            if item.service.id == service_id:
                if item.count <= 0:
                    raise ValidationDict211Error('次卡已无次数')
                else:
                    break
        else:
            raise ValidationDict211Error('无次卡')

        # TODO record count card
        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def recharge_history(self, request, *args, **kwargs):
        serializer = TimeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter = Q(trade__shop_id=kwargs['pk_shop']) & Q(status='pay')
        if 'begin_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__gte=serializer.validated_data['begin_time'])
        if 'end_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__lt=serializer.validated_data['end_time'])

        queryset = TradeMemberProfile.objects.filter(filter).order_by('-trade')

        return response_page(self, MemberRechargeHistoryAppSerializer, queryset)

    @detail_route(methods=['get'])
    @shop_member_manage_only
    def person_recharge_history(self, request, pk_shop, pk):
        serializer = TimeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        user_id = ShopMember.objects.get(pk=pk).user_id
        filter = Q(trade__shop_id=pk_shop) &Q(trade__buyer_id=user_id) & Q(status='pay')
        if 'begin_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__gte=serializer.validated_data['begin_time'])
        if 'end_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__lt=serializer.validated_data['end_time'])

        queryset = TradeMemberProfile.objects.filter(filter).order_by('-trade')

        return response_page(self, MemberRechargeHistoryAppSerializer, queryset)

    @list_route(methods=['get'])
    def consume_history(self, request, *args, **kwargs):
        serializer = TimeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter = Q(trade__shop_id=kwargs['pk_shop']) & Q(pay_type='member')
        if 'begin_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__gte=serializer.validated_data['begin_time'])
        if 'end_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__lt=serializer.validated_data['end_time'])

        queryset = TradePay.objects.filter(filter).order_by('-id')

        return response_page(self, MemberConsumeHistoryAppSerializer, queryset)

    @detail_route(methods=['get'])
    @shop_member_manage_only
    def person_consume_history(self, request, pk_shop, pk):
        serializer = TimeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        user_id = ShopMember.objects.get(pk=pk).user_id
        filter = Q(trade__shop_id=pk_shop) &Q(trade__buyer_id=user_id) &Q(pay_type='member') &Q(trade__profile_type='discount')
        if 'begin_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__gte=serializer.validated_data['begin_time'])
        if 'end_time' in serializer.validated_data.keys():
            filter = filter & Q(trade__trade_time__lt=serializer.validated_data['end_time'])

        queryset = TradePay.objects.filter(filter).order_by('-id')

        return response_page(self, MemberConsumeHistoryAppSerializer, queryset)

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def remark(self, request, pk_shop, pk):
        remark = request.data['remark']

        instance = self.get_object()
        instance.remark = remark
        instance.save(update_fields=['remark'])

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    @shop_member_manage_only
    def card(self, request, pk_shop, pk):
        card_id = request.data['card']
        temp = ShopMemberCard.objects.filter(shop_id=pk_shop, id=card_id).exists()
        if temp:
            ShopMember.objects.filter(shop_id=pk_shop, id=pk).update(member_card_id=card_id)
        else:
            raise ValidationDict211Error('新卡不存在')

        return Response({'result': 'OK'})
