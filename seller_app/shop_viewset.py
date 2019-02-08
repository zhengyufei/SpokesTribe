import decimal, datetime

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from APNS import apns, apns_push
from SpokesTribe.settings import SHOP_WITHDRAW
from MyAbstract.exceptions import ValidationDict211Error
from common.models import Shop, ShopSpoke, ShopDiscount, ShopSpokeGroup, ShopRequire, \
    TradeTicketProfile, TradeExperienceProfile, TradeRecord, Wallet, ShopWallet, Flyer2User, Trade, ShopFlyer, Flyer2Shop
from common.function import response_page
from common.serializers import ShopFaceSerializer

from .function import base_bill_app
from .serializers import HomeAppSerializer, ShopRequireAppSerializer, BonusSerializer, ShopSerializer, \
    ShopRequireSerializer, ShopDiscountSerializer, BaseBillAppSerializer, ConfirmTicketSerializer, ShopListAppSerializer
from .permission import IsManager


class ShopViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopSerializer

    def list(self, request, *args, **kwargs):
        queryset = Shop.objects.filter(managers=request.user, state__in=(1, 2, 4, 5))
        for item in queryset:
            item.is_seller = (item.seller == request.user)

        return response_page(self, ShopListAppSerializer, queryset)

    @detail_route(methods=['get'])
    def manage(self, request, pk):
        shop = Shop.objects.get(pk=pk, managers=request.user)
        shop.is_seller = (shop.seller_id == request.user.id)
        shop.is_manager = shop.managers.filter(id=request.user.id).exists()

        bill = BaseBillAppSerializer()
        bill.my_init(base_bill_app(shop.id))

        home = HomeAppSerializer()
        home.my_init(shop, bill)

        serializer = HomeAppSerializer(home, context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['get', 'post'])
    def require(self, request, pk=None):
        if request.method == 'GET':
            return self.get_require(request, pk=pk)
        elif request.method == 'POST':
            return self.set_require(request, pk=pk)

    @detail_route(methods=['get'])
    def require2(self, request, pk=None):
        try:
            require = ShopRequire.objects.get(shop_id=pk)
        except ShopRequire.DoesNotExist:
            raise ValidationDict211Error('error')

        serializer = ShopRequireAppSerializer(require)

        return Response(serializer.data)

    def get_require(self, request, pk=None):
        try:
            require = ShopRequire.objects.get(shop_id=pk)
        except:
            raise ValidationDict211Error('error')

        serializer = ShopRequireSerializer(require)

        return Response(serializer.data)

    def set_require(self, request, pk=None):
        require = ShopRequire.objects.get(pk=pk)

        serializer = ShopRequireSerializer(instance=require, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'detail': 'OK'})

    @detail_route(methods=['get', 'post'])
    def discount(self, request, pk=None):
        if request.method == 'GET':
            return self.get_discount(request, pk=pk)
        elif request.method == 'POST':
            return self.set_discount(request, pk=pk)

    def get_discount(self, request, pk=None):
        discount = ShopDiscount.objects.get(pk=pk)
        serializer = ShopDiscountSerializer(discount, context=self.get_serializer_context())
        return Response(serializer.data)

    def set_discount(self, request, pk=None):
        instance = ShopDiscount.objects.get(pk=pk)
        serializer = ShopDiscountSerializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.update(instance, serializer.validated_data)

        queryset = ShopSpoke.objects.filter(shop=pk, type='normal')
        queryset = ShopSpokeGroup.objects.select_for_update().filter(shop=pk, group__user__in=[obj.spokesman.id for obj in queryset])

        # todo
        for item in queryset:
            if instance.is_valid:
                if 1 == instance.type:
                    tmp = 1 if instance.discount >= 100 else \
                        (item.discount - instance.discount) / decimal.Decimal(
                        100.0 - instance.discount)
                elif 2 == instance.type:
                    tmp = 1 if instance.reduce_price <= 0 else \
                        (instance.reduce_price - item.discount) / decimal.Decimal(
                        instance.reduce_price)
            else:
                tmp = 1

            if serializer.validated_data['is_valid']:
                type = serializer.validated_data['type']
                if 1 == type:
                    discount = serializer.validated_data['discount']
                    item.discount = 100 * tmp - tmp * discount + discount
                elif 2 == type:
                    reduce = serializer.validated_data['reduce_price']
                    item.discount = reduce - tmp * reduce

                item.save(update_fields=['discount'])

        return Response({'detail': 'OK'})

    @detail_route(methods=['get'])
    def base_bill_app(self, request, pk=None):
        bill = BaseBillAppSerializer()
        bill.my_init(base_bill_app(pk))

        serializer = BaseBillAppSerializer(bill)

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def confirm_tickets(self, request, pk):
        serializer = ConfirmTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        combos = []
        experiences = []

        for item in serializer.validated_data['tickets']:
            if 12 == len(item):
                combos.append(item)
            elif 14 == len(item):
                experiences.append(item)
            else:
                raise ValidationDict211Error('券无效')

        shop = Shop.objects.get(pk=pk)

        if len(combos) > 0:
            self.combo(shop, combos)

        if len(experiences) > 0:
            self.experience(shop, experiences)

        return Response({'detail': 'OK'})

    def combo(self, shop, tickets):
        old_tickets = tickets
        tickets = TradeTicketProfile.objects.filter(ticket_number__in=old_tickets, trade__shop=shop, status='pay')
        count = tickets.count()
        if 0 == count or len(old_tickets) != count:
            raise ValidationDict211Error('劵信息错误1', 'tickets count error')

        shop_earning = decimal.Decimal(0)

        trade = tickets[0].trade
        brokerage_type = trade.shop.brokerage_type
        for item in tickets:
            if 2 == brokerage_type:
                item.confirm(trade.charge_ratio, trade.brokerage_ratio)

            shop_earning += item.shop_earning

            Wallet.income_pay(item.trade.spokesman_id, item.brokerage)

            record = TradeRecord.objects.create(ticket=item, confirm=True)
            apns_push.handle_trade_ticket_use(record)

        ShopWallet.income_pay(shop, shop_earning)

        if 1 == brokerage_type:
            tickets.update(status='confirm', confirm_time=datetime.datetime.now())

    def experience(self, shop, tickets):
        old_tickets = tickets
        tickets = Flyer2User.objects.filter(ticket_number__in=old_tickets, flyer__shop=shop, status='valid')
        count = tickets.count()
        if 0 == count or len(old_tickets) != count:
            raise ValidationDict211Error('劵信息错误2', 'tickets count error')

        buyer = tickets[0].user

        trade = Trade.objects.create(profile_type='experien', shop=shop, buyer=buyer, spokesman=shop.seller,
             total_fee=0, trade_price=0, has_pay=True)

        for item in tickets:
            TradeExperienceProfile.objects.create(trade=trade, trade_price=0, discount_reduce=0,
                shop_earning=0, status='confirm', ticket=item)

            wallet = ShopWallet.objects.select_for_update().get(shop=shop)

            if wallet.bonus_pool >= item.flyer.bonus:
                wallet.bonus_pool -= item.flyer.bonus
                wallet.save(update_fields=['bonus_pool'])
                ShopWallet.income_bonus(item.shop.id, item.flyer.bonus)
                item.status = 'settled'
                item.save(update_fields=['status'])
            else:
                wallet.bonus_pool -= item.flyer.bonus
                wallet.save(update_fields=['bonus_pool'])

                queryset = ShopFlyer.objects.filter(shop=item.flyer.shop)
                Flyer2Shop.objects.filter(flyer__in=queryset).delete()
                queryset.update(status='invalid', left_time=timezone.now())

        tickets.update(status='used')

    @detail_route(methods=['get'])
    def bonus(self, request, pk):
        temp = BonusSerializer()
        wallet = ShopWallet.objects.get(pk=pk)
        temp.bonus = wallet
        temp.bonus.attention = '1. 每月免提现额度{0}，超出额度将收取{1}%手续费\n2. 余额包含商家联盟收入，余额2元以上可提现\n3. 0元及以下将暂停使用商家联盟'.format(
            wallet.max_bonus_free, decimal.Decimal(SHOP_WITHDRAW*100).quantize(decimal.Decimal('0.00')))
        temp.discount = ShopDiscount.objects.get(pk=pk)

        serializer = BonusSerializer(temp)
        return Response(serializer.data)

    @detail_route(methods=['get', 'post'])
    def face(self, request, pk):
        if request.method == 'GET':
            return self.get_face(request, pk=pk)
        elif request.method == 'POST':
            return self.set_face(request, pk=pk)

    def get_face(self, request, pk=None):
        try:
            shop = Shop.objects.get(pk=pk)
        except:
            raise ValidationDict211Error('error', detail_en='error')

        serializer = ShopFaceSerializer(shop, context=self.get_serializer_context())

        return Response(serializer.data)

    def set_face(self, request, pk=None):
        serializer = ShopFaceSerializer(data=request.data)
        serializer.is_valid(True)

        serializer.update(Shop.objects.get(pk=pk), serializer.validated_data)

        return Response({'detail': 'OK'})

    @detail_route(methods=['get', 'post'])
    def convenience(self, request, pk):
        if request.method == 'GET':
            return self.get_convenience(request, pk=pk)
        elif request.method == 'POST':
            return self.set_convenience(request, pk=pk)

    def get_convenience(self, request, pk=None):
        try:
            shop = Shop.objects.get(pk=pk)
        except:
            raise ValidationDict211Error('error', detail_en='error')

        return Response({'convenience': shop.convenience})

    def set_convenience(self, request, pk=None):
        if 'convenience' not in request.data:
            raise ValidationDict211Error('error')

        Shop.objects.filter(pk=pk).update(convenience = request.data['convenience'])

        return Response({'detail': 'OK'})

    @detail_route(methods=['get', 'post'])
    def announcement(self, request, pk):
        if request.method == 'GET':
            return self.get_announcement(request, pk=pk)
        elif request.method == 'POST':
            return self.set_announcement(request, pk=pk)

    def get_announcement(self, request, pk=None):
        try:
            shop = Shop.objects.get(pk=pk)
        except:
            raise ValidationDict211Error('error', detail_en='error')

        return Response({'announcement': shop.announcement})

    def set_announcement(self, request, pk=None):
        if 'announcement' not in request.data:
            raise ValidationDict211Error('error')

        Shop.objects.filter(pk=pk).update(announcement=request.data['announcement'])

        return Response({'detail': 'OK'})