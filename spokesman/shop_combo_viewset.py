from django.db import connection
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import detail_route
from rest_framework.response import Response
import common.permission
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl
from common.models import create_trade_number, MyUser, Shop, ShopCombo, Trade, TradeTicketProfile, ShopMemberCard, ShopDiscount
from common.function import spoker_type, discount_describe_friend
from .function import calculate, calculate_trade_dict_discount
from .serializers import ShopWithSpokesSerializer, ShopComboSerializer, CompleteTradeComboSerializer, \
    TradeComboCalculateSerializer, TradeComboResponseSerializer
from .permission import combo_time
from .shop_discount import ShopDiscountCalculate
from MyAbstract.funtions import fenceil, fenfloor


class ShopComboViewSet(mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopCombo.objects.all()
    permission_classes = [permissions.IsAuthenticated, common.permission.ShopComboOnline]
    serializer_class = ShopComboSerializer

    def retrieve(self, request, *args, **kwargs):
        shop_with_spokes = ShopWithSpokesSerializer(data=request.query_params)
        shop_with_spokes.is_valid(raise_exception=True)

        instance = self.get_object()
        shop_id = kwargs['pk_shop']
        shop = Shop.objects.get(pk=shop_id)

        instance.shop_name = shop.name
        instance.shop_address = shop.address
        instance.shop_phone = shop.phone

        spokesman_id = None
        if 'spokesman_id' in shop_with_spokes.validated_data:
            spoke_type = spoker_type(shop_id, shop_with_spokes.validated_data['spokesman_id'])
            if spoke_type:
                spokesman_id = shop_with_spokes.validated_data['spokesman_id']

        if not spokesman_id:
            spokesman_id = shop.seller_id

        spoker = MyUser.objects.get(pk=spokesman_id)
        instance.spokesman_id = spoker.id
        instance.spokesman_ico = GetAbsoluteImageUrl(request, spoker.ico_thumbnail)

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    def __trade_dict(self, shop_id, combo_id):
        total = Shop.objects.get(pk=shop_id).combo.get(pk=combo_id).activity_price
        trade_dict = calculate_trade_dict_discount(total, False, 1, 100, 100, 0, 1, True)

        return trade_dict

    def enlarge(self, trade_dict, count):
        trade_dict['trade_price'] *= count
        trade_dict['discount_reduce'] *= count
        trade_dict['brokerage'] *= count

        return trade_dict

    @detail_route(methods=['post'])
    @combo_time
    def calculate(self, request, pk_shop, pk):
        serializer = CompleteTradeComboSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = serializer.validated_data['count']
        trade_dict = self.__trade_dict(pk_shop, pk)
        trade_dict = self.enlarge(trade_dict, count)

        serializer = TradeComboCalculateSerializer(trade_dict)

        return Response(serializer.data)

    @detail_route(methods=['post'])
    @combo_time
    def trade(self, request, pk_shop, pk):
        serializer = CompleteTradeComboSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trade = self.__trade(request, pk_shop, pk, serializer)
        discount_reduce = trade.tickets.all()[0].discount_reduce * trade.tickets.count()

        serializer=TradeComboResponseSerializer({'id': trade.trade_number, 'name': ShopCombo.objects.get(pk=pk).name,
                         'price': trade.trade_price, 'ico': GetAbsoluteImageUrl(request, trade.shop.ico_thumbnail),
                         'discount_reduce': discount_reduce})

        return Response(serializer.data)

    def __trade(self, request, pk_shop, pk, serializer):
        spoke_type = spoker_type(pk_shop, serializer.validated_data['spokesman'])
        if spoke_type:
            spoker_id = serializer.validated_data['spokesman']
        else:
            raise ValidationDict211Error('代言人不存在', detail_en='the man is fake')

        self.client_price = serializer.validated_data['client_price'] \
            if hasattr(serializer.validated_data, 'client_price') else None

        count = int(serializer.validated_data['count'])
        combo = ShopCombo.objects.get(id=pk, shop_id=pk_shop)
        total = combo.activity_price * count
        trade_dict = self.__trade_dict(pk_shop, pk)
        trade = self.create_trade(pk_shop, pk, request.user.id, spoker_id, count, total, trade_dict)

        return trade

    def create_trade(self, shop_id, combo_id, buyer_id, spoker_id, count, total, trade_dict):
        trade = Trade.objects.create(profile_type='ticket', shop_id=shop_id, buyer_id=buyer_id, spokesman_id=spoker_id,
            shop_discount=trade_dict['shop_discount'] if trade_dict['is_discount'] else None,
            discount=trade_dict['spokesman_discount'] if trade_dict['is_discount'] else None,
            total_fee=total, trade_price=trade_dict['trade_price'] * count)

        for i in range(count):
            profile = TradeTicketProfile.objects.create\
                (shop_id=shop_id, trade=trade, combo_id=combo_id, trade_price=trade_dict['trade_price'],
                 discount_reduce=trade_dict['discount_reduce'], brokerage_design=trade_dict['brokerage'])

            trade.tickets.add(profile)

        #if self.client_price and self.client_price != trade.trade_price:
        #    Logger.Log('warning', 'trade price {0} {1} {2}'.format(trade.id, trade.trade_price, self.client_price))

        return trade
