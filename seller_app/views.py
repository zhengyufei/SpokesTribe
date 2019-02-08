# Create your views here.
import decimal
import json

from django.db import connection
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import status,viewsets, permissions, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

import common.views
from APNS import apns
from Bankcard.bankcard import verify_bankcard
from SpokesTribe.settings import SHOP_WITHDRAW
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl, calcDistance, decimal2string, timetuple_utc
from Pay.Ali import alipay
from Pay.Integrated.Zhaoshang import ZhaoBank
from Pay.Weixin import weixinpay
from Pay.Zhaoshang.ZhaoshangTransfer import PayForAnother
from RedisIF.RedisIF import RedisIF
from SMS import SMS
from common.function import response_page, response_list
from common.models import create_trade_number, MyUser, Shop, ShopSpokeRequest, ShopSpoke, ShopSpokeRequestHistory, \
    Wallet, FriendGroup, ShopSpokeGroup, ShopWallet, ShopBankCard, Trade, \
    ShopCombo, TradeTicketProfile, TradeDiscountProfile, TradeRecord, \
    ShopCashRecord, TradeShop, TradeShopPay, ShopFlyer, ShopFlyerDiscountProfile, ShopFlyerReduceProfile, \
    ShopFlyerExperienceProfile, ShopFlyerExperienceGoods, Flyer2Shop, TradeExperienceProfile, CurrentVersion, TradeMemberProfile, \
    ShopManagerShip, ShopWithdrawRecord, ShopPhoto, MyUserSellerSettingProfile
from common.refund import Refund
from common.serializers import EmptySerializer, BankcardSerializer, TradePayResponseSerializer, ShopPhotoSerializer, \
    DelIDsSerializer, ShopPhotoAddListSerializer
from .function import base_bill_app
from .permission import IsSeller, IsManager, shop_manage
from .serializers import ShopRequestJudgeSerializer, WalletLooseChangeSerializer, WalletBonusSerializer, \
    TradeDiscountSerializer, TradeFilterSerializer, ShopComboSerializer, TradeTicketSerializer, \
    BindBankcardSerializer, SetMinCashSerializer, CashRecordSerializer, CashRecordListSerializer, BounsPoolSerializer, \
    TradeShopSerializer, ShopFlyerSerializer, ShopFlyerNearbySerializer, \
    ShopFlyerDiscountSerializer, ShopFlyerReduceSerializer, ShopFlyerExperienceSerializer, \
    Flyer2ShopMineSerializer, Flyer2ShopOhterSerializer, ShopFlyerProfileSerializer, FlyerTradeMineSerializer, FlyerTradeOtherSerializer, \
    Interface1RequestSerializer, Interface1ResponseSerializer, HomeAppSerializer, BaseBillAppSerializer, TradeExperienceSerializer, \
    ShopManagerSerializer, ShopSpokerListSerializer, ShopSpokerSerializer, ShopSpokeRequestListSerializer, \
    ShopSpokesRequestAppSerializer, ShopSpokerResumeSerializer, ShopComboListSerializer, TradeSerializer, \
    TradeMemberSerializer, TradeBonusSerializer, ShopManagerCreateSerializer, WithdrawRecordSerializer, \
    InformationSerializer, SettingSerializer, FlyerFilterSerializer
import common.settings as my_settings


class SmsVerifyViewSet(common.views.SmsVerifyViewSet):
    def send_sms(self, phone, type, code):
        sms = SMS.SellerSMS()
        self.base_send_sms(sms, phone, type, code)


class InterfaceViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def manager(self, request, *args, **kwargs):
        try:
            if 'shop' in request.query_params:
                shop_id = int(request.query_params['shop'])
                shop = Shop.objects.get(pk=shop_id, managers=request.user)
            else:
                shop = Shop.objects.filter(state=4, managers=request.user)[0]
            shop.is_seller = (shop.seller_id == request.user.id)
            shop.is_manager = Shop.managers.filter(id=request.user.id).exists()
            bill = BaseBillAppSerializer()
            bill.my_init(base_bill_app(shop.id))

            home = HomeAppSerializer()
            home.my_init(shop, bill)

            serializer = HomeAppSerializer(home, context=self.get_serializer_context())
            return Response(serializer.data)
        except:
            return Response({})

    @list_route(methods=['post'])
    def mine(self, request, *args, **kwargs):
        serializer = Interface1RequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        type=serializer.validated_data['type']

        serializer = Interface1ResponseSerializer()
        serializer.version = CurrentVersion.objects.get(type=type).version
        serializer.no_disturb = request.user.myusersellersettingprofile.no_disturb
        serializer.apns_voice = request.user.myusersellersettingprofile.apns_voice

        serializer = Interface1ResponseSerializer(serializer)
        return Response(serializer.data)

    @list_route(methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def information(self, request, *args, **kwargs):
        serializer = InformationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = MyUserSellerSettingProfile.objects.get(user=request.user)
        serializer.update(profile, serializer.validated_data)

        return Response({'result': 'OK'})

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def apns_voice(self, request, *args, **kwargs):
        serializer = SettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'apns_voice' in serializer.validated_data.keys():
            MyUserSellerSettingProfile.objects.filter(user=request.user).update(apns_voice=serializer.validated_data['apns_voice'])
        else:
            raise ValidationDict211Error('missing voice')

        return Response({'result': 'OK'})

class ShopComboViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    class_name = ShopCombo
    queryset = ShopCombo.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopComboSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.class_name.objects.filter(shop_id=kwargs['pk_shop'], shop__managers=request.user, status__in=('ready', 'online'))
        serializer = ShopComboListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results':serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(shop_id=kwargs['pk_shop'])
        return Response({'detail': 'OK'},status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance, context=self.get_serializer_context())
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_ready():
            raise ValidationDict211Error('不是准备阶段', detail_en='combo is not ready')

        return mixins.UpdateModelMixin.update(self, request, *args, **kwargs)

    @detail_route(methods=['post'])
    def online(self, request, pk_shop, pk):
        instance = self.get_object()
        if not instance.is_ready():
            raise ValidationDict211Error('不是准备阶段', detail_en='combo is not ready')

        instance.status = 'online'
        instance.save(update_fields=['status'])

        return Response({'result': 'OK'})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        instance.status = 'offline'
        instance.save(update_fields=['status'])

        return Response(status=status.HTTP_204_NO_CONTENT)

class ShopRequestViewSet(mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    class_name = ShopSpokeRequest
    queryset = ShopSpokeRequest.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopSpokesRequestAppSerializer

    def list(self, request, *args, **kwargs):
        queryset = MyUser.objects.filter(resume__request__shop=kwargs['pk_shop'])

        return response_page(self, ShopSpokeRequestListSerializer, queryset)

    def retrieve(self, request, *args, **kwargs):
        try:
            spoke_request = self.class_name.objects.get(shop_id=kwargs['pk_shop'], resume__user_id=kwargs['pk'])
        except self.class_name.DoesNotExist:
            raise ValidationDict211Error('error')

        user = MyUser.objects.get(pk=kwargs['pk'])
        user.request_time = spoke_request.request_time
        serializer = self.serializer_class(user, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def judge(self, request, pk_shop, pk):
        shop = Shop.objects.get(pk=pk_shop)
        if shop.spoke_count >= shop.max_spoke:
            raise ValidationDict211Error('代言人数已经达到上线')

        serializer = ShopRequestJudgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        judge = serializer.validated_data['judge']
        obj = self.class_name.objects.get(resume__user_id=pk, shop_id=pk_shop)
        spoker = obj.resume.user
        ShopSpokeRequestHistory.objects.create(shop=obj.shop, spokesman=spoker, request_time=obj.request_time, result=judge)

        if judge:
            ShopSpoke.objects.create(shop=obj.shop, spokesman=spoker, type='normal')
            discount = 0.5 * obj.shop.discount.discount + 50 if 1 == obj.shop.discount.type else 0.5 * obj.shop.discount.reduce_price
            ShopSpokeGroup.objects.create(shop_id=pk_shop, group=FriendGroup.objects.get(user=spoker, type=3), discount=discount)
            # todo
            Shop.objects.filter(id=pk_shop).update(spoke_count=ShopSpoke.objects.filter(shop_id=pk_shop).count())
            apns.publish_apply_spokesman(spoker, spoker.nick_name, obj.shop.name)

        obj.delete()

        return Response({'detail': 'OK'})

class ShopSpokerViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.GenericViewSet):
    class_name = ShopSpoke
    queryset = ShopSpoke.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopSpokerSerializer

    def list(self, request, *args, **kwargs):
        shop = Shop.objects.get(pk=kwargs['pk_shop'])

        sql = "SELECT U.id, U.ico_thumbnail, U.nick_name, SM.id, TE.count_id, TE.sum_trade "\
            "FROM common_myuser AS U "\
            "LEFT JOIN (SELECT spokesman_id, COUNT(T.id) AS count_id, SUM(T.trade_price) as sum_trade "\
            "FROM common_trade AS T LEFT JOIN common_tradediscountprofile AS TD ON T.id = TD.trade_id "\
            "WHERE DATE_FORMAT(T.trade_time,'%Y%m') = date_format(now(),'%Y%m') AND T.shop_id = {0} AND TD.`status` in ('pay', 'confirm') "\
            "AND T.spokesman_id IN (SELECT spokesman_id FROM common_shopspoke WHERE shop_id = {0}) "\
            "GROUP BY spokesman_id) AS TE ON U.id = TE.spokesman_id "\
            "LEFT JOIN common_shopmanagership AS SM ON U.id = SM.user_id AND SM.shop_id = {0} "\
            ", common_shopspoke AS S2, common_shop AS S3 "\
            "WHERE U.id = S2.spokesman_id AND S2.shop_id = {0} AND S2.shop_id = S3.id "\
            "ORDER BY SM.id DESC ".format(int(kwargs['pk_shop']))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        queryset = []

        for obj in fetchall:
            serializer = ShopSpokerListSerializer()
            serializer.id = obj[0]
            serializer.ico = GetAbsoluteImageUrl(request, obj[1])
            serializer.name = obj[2]
            serializer.is_seller = (shop.seller_id == serializer.id)
            serializer.is_manager = (bool)(obj[3])
            serializer.count = obj[4] if obj[4] else 0
            serializer.sale = decimal2string(obj[5]) if obj[5] else '0'

            queryset.append(serializer)

        return response_page(self, ShopSpokerListSerializer, queryset)

    def retrieve(self, request, *args, **kwargs):
        sql = "SELECT U.id, U.ico_thumbnail, U.nick_name, U.phone_number, S2.begin_time, SM.id, TE.count_id, TE.sum_trade, TE.sum_brokerage, S3.seller_id " \
              "FROM common_myuser AS U " \
              "LEFT JOIN (SELECT spokesman_id, COUNT(T.id) AS count_id, SUM(T.trade_price) as sum_trade , SUM(TD.brokerage) as sum_brokerage " \
              "FROM common_trade AS T LEFT JOIN common_tradediscountprofile AS TD ON T.id = TD.trade_id " \
              "WHERE DATE_FORMAT(T.trade_time,'%Y%m') = date_format(now(),'%Y%m') AND T.shop_id = {0} AND TD.`status` in ('pay', 'confirm') " \
              "AND T.spokesman_id IN (SELECT spokesman_id FROM common_shopspoke WHERE shop_id = {0}) " \
              "GROUP BY spokesman_id) AS TE ON U.id = TE.spokesman_id " \
              "LEFT JOIN common_shopmanagership AS SM ON U.id = SM.user_id AND SM.shop_id = {0} " \
              ", common_shopspoke AS S2, common_shop AS S3 " \
              "WHERE U.id = S2.spokesman_id AND S2.shop_id = {0} AND S2.shop_id = S3.id AND U.id = {1} ".format(int(kwargs['pk_shop']), int(kwargs['pk']))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        try:
            obj = fetchall[0]
        except:
            raise ValidationDict211Error('error')

        serializer = self.serializer_class()
        serializer.id = obj[0]
        serializer.ico = GetAbsoluteImageUrl(request, obj[1])
        serializer.name = obj[2]
        serializer.phone = obj[3]
        serializer.begin_time = timetuple_utc(obj[4])
        serializer.is_manager = (bool)(obj[5])
        serializer.count = obj[6] if obj[6] else 0
        serializer.sale = decimal2string(obj[7]) if obj[7] else '0'
        serializer.brokerage = decimal2string(obj[8]) if obj[8] else '0'
        serializer.is_seller = (obj[9] == serializer.id)

        serializer = self.serializer_class(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            ShopSpoke.objects.get(spokesman_id=kwargs['pk'], shop_id=kwargs['pk_shop']).delete()
        except ShopSpoke.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        try:
            ShopSpokeGroup.objects.get(group__user_id=kwargs['pk'], shop_id=kwargs['pk_shop']).delete()
        except ShopSpokeGroup.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        Shop.objects.filter(pk=kwargs['pk_shop']).update(spoke_count=F('spoke_count')-1)

        return Response({'result': 'OK'})

    @detail_route(methods=['get'])
    def resume(self, request, pk_shop, pk):
        if not (ShopSpoke.objects.filter(Q(shop_id=pk_shop) & (Q(spokesman_id=pk) | Q(member__user_id=pk)))).exists():
            raise ValidationDict211Error('error')

        user = MyUser.objects.get(pk=pk)
        serializer = ShopSpokerResumeSerializer(user, context=self.get_serializer_context())

        return Response(serializer.data)

class WalletViewSet(viewsets.GenericViewSet):
    queryset = Wallet.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = WalletLooseChangeSerializer

    @list_route(methods=['get'])
    def loose_change(self, request, *args, **kwargs):
        wallet = ShopWallet.objects.get(shop_id=kwargs['pk_shop'])
        serializer = WalletLooseChangeSerializer(wallet)

        return Response(serializer.data)

    @list_route(methods=['post'])
    def set_min_cash(self, request, *args, **kwargs):
        serializer = SetMinCashSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ShopWallet.objects.filter(shop_id=kwargs['pk_shop']).update(min_cash=serializer.validated_data['min_cash'])

        return Response({'detail': 'OK'})

    @list_route(methods=['get', 'post'])
    def bonus(self, request, *args, **kwargs):
        if request.method == 'GET':
            return self.get_bonus(request, *args, **kwargs)
        elif request.method == 'POST':
            return self.set_bonus(request, *args, **kwargs)

    def get_bonus(self, request, *args, **kwargs):
        wallet = ShopWallet.objects.get(shop_id=kwargs['pk_shop'])
        serializer = WalletBonusSerializer(wallet)

        return Response(serializer.data)

    def set_bonus(self, request, *args, **kwargs):
        # 1 weixin 2 zhifubao 3 weixin_pa 4 zhaoshang 5 member 6 zhaobank_weixin 7 zhaobank_ali
        serializer = BounsPoolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trade_price = serializer.validated_data['total_fee']
        pay_type = serializer.validated_data['pay_type']

        serializer = None
        trade = TradeShop.objects.create(shop_id=kwargs['pk_shop'], trade_price=trade_price,
                                         trade_number=create_trade_number())

        if pay_type == 1:
            serializer = self.weixin(trade)
        elif pay_type == 2:
            serializer = self.ali(trade)
        elif pay_type == 6:  # zhangbank + weixin
            token = Token.objects.get(user=request.user)
            serializer = self.zhaobank(trade, pay_type, token.key)
        elif pay_type == 7:  # zhangbank + ali
            token = Token.objects.get(user=request.user)
            serializer = self.zhaobank(trade, pay_type, token.key)

        if serializer:
            serializer = TradePayResponseSerializer(serializer)
            return Response(serializer.data)
        else:
            raise ValidationDict211Error('not find trade')

    def weixin(self, trade):
        TradeShopPay.objects.create(trade=trade, pay_type='weixin')
        serializer = TradePayResponseSerializer()
        serializer.sign = weixinpay.SellerPay().pay_sign(trade.id, trade.trade_number, trade.trade_price)

        return serializer

    def ali(self, trade):
        TradeShopPay.objects.create(trade=trade, pay_type='ali')
        serializer = TradePayResponseSerializer()
        serializer.sign = alipay.SellerPay().pay_sign(trade.id, trade.trade_number, trade.trade_price)

        return serializer

    def zhaobank(self, trade, type, token):
        open_id = ZhaoBank.PayConf.mine_open_id
        open_key = ZhaoBank.PayConf.mine_open_key

        pay = ZhaoBank.Pay(open_id, open_key, trade.trade_number, type, trade.trade_price, token, 'shop', shop_id=trade.shop_id)
        res = pay.getResponse()
        # same as TradePay
        pay_type = 'zb_wx' if type == 6 else 'zb_ali'
        TradeShopPay.objects.create(trade=trade, pay_type=pay_type, zhaobank_no=res['ord_no'])

        serializer = TradePayResponseSerializer()
        serializer.url = res['jsapi_pay_url']

        return serializer

    @list_route(methods=['post'])
    def withdraw(self, request, *args, **kwargs):
        wallet = ShopWallet.objects.select_for_update().get(shop_id=kwargs['pk_shop'])

        if not hasattr(wallet, 'bankcard'):
            raise ValidationDict211Error('还没有绑定银行卡')

        if not wallet.bankcard.is_valid:
            raise ValidationDict211Error('银行卡信息有误，请先更正')

        if wallet.bonus_pool < decimal.Decimal(2):
            raise ValidationDict211Error('可提额度不足')

        bonus = wallet.bonus_pool
        wallet.bonus_pool = 0
        wallet.bonus_withdraw += bonus
        wallet.save(update_fields=['bonus_pool', 'bonus_withdraw'])

        temp = min(wallet.bonus_withdraw - wallet.max_bonus_free, bonus)
        if temp > 0:
            plat_ratio = SHOP_WITHDRAW
            charge = temp * plat_ratio
            cash = bonus - charge
        else:
            charge = 0
            cash = 0

        record = ShopWithdrawRecord.objects.create(shop_id=wallet.shop_id, loose_change=bonus, cash=cash,
              status='request', charge=charge, request_bank_name=wallet.bankcard.bank.name,
              request_acc_name=wallet.bankcard.name, request_acc_no=wallet.bankcard.card)

        response = PayForAnother(record.number, wallet.bankcard.bank.name, wallet.bankcard.card, wallet.bankcard.name,
                                 cash)
        response = json.loads(str(response.post(), encoding="utf-8"))

        record.merch_time = timezone.now()
        record.bank_name = wallet.bankcard.bank.name
        record.acc_no = wallet.bankcard.card
        record.acc_name = wallet.bankcard.name
        record.status = 'apply'
        record.handle_time = timezone.now()
        record.retcod = response['RETCOD']
        record.errmsg = response['ERRMSG']
        if record.retcod != 'S':
            record.status = 'fail'
        record.save(update_fields=['merch_time', 'bank_name', 'acc_no', 'acc_name',
                                   'status', 'handle_time', 'retcod', 'errmsg', 'status'])

        queryset = ShopFlyer.objects.filter(shop_id=kwargs['pk_shop'], status='online')
        queryset.update(status='limit', left_time=timezone.now())

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def withdraw_record(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        shop_id = kwargs['pk_shop']

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter_time = " AND request_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        sql = "SELECT id, request_time, cash FROM common_shopwithdrawrecord WHERE shop_id = {0} {1} " \
              "ORDER BY id DESC ".format(shop_id, filter_time)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for item in fetchall:
            tmp = WithdrawRecordSerializer()
            tmp.time = timetuple_utc(item[1])
            tmp.amount = item[2]

            serializers.append(tmp)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = WithdrawRecordSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = WithdrawRecordSerializer(serializers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    @list_route(methods=['get', 'post'])
    def card(self, request, *args, **kwargs):
        if request.method == 'GET':
            return self.get_card(request, *args, **kwargs)
        elif request.method == 'POST':
            return self.set_card(request, *args, **kwargs)

    @list_route(methods=['post'])
    def set_card(self, request, *args, **kwargs):
        serializer = BindBankcardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = ShopWallet.objects.get(shop_id=kwargs['pk_shop'])

        has_card = hasattr(wallet, 'bankcard')
        if has_card and wallet.bankcard.is_valid:
            raise ValidationDict211Error('已绑定卡片')

        verify = verify_bankcard(serializer.validated_data['card_name'])

        if not verify[0]:
            verify = (False, 'unknow', 'unknow', 'unknow')

        if not has_card:
            ShopBankCard.objects.create(wallet=wallet, bank=verify[1], type=verify[2], code=verify[3],
                card=serializer.validated_data['card_name'], name=serializer.validated_data['master_name'],
                phone=serializer.validated_data['phone'])
        else:
            ShopBankCard.objects.filter(wallet=wallet).update(bank=verify[1], type=verify[2], code=verify[3],
                card=serializer.validated_data['card_name'], name=serializer.validated_data['master_name'],
                phone=serializer.validated_data['phone'], is_valid=True)

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def get_card(self, request, *args, **kwargs):
        wallet = ShopWallet.objects.get(shop_id=kwargs['pk_shop'])

        if not hasattr(wallet, 'bankcard'):
            raise ValidationDict211Error('未绑定卡片')

        serializer = BankcardSerializer()

        serializer.bank_name = wallet.bankcard.bank.name
        serializer.ico = wallet.bankcard.bank.image
        serializer.card_type = wallet.bankcard.type
        serializer.simple_card = wallet.bankcard.card[-4:]

        serializer = BankcardSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = TradeRecord.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        shop_id = kwargs['pk_shop']

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        pay_type = serializer.validated_data['pay_type'] if 'pay_type' in serializer.validated_data.keys() else None
        filter_time = " AND T.trade_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        filter_pay_type = ''
        if 'wx' == pay_type:
            filter_pay_type = " AND TP.pay_type in {0}".format(common.settings.pay_type_reversal['微信'])
        elif 'ali' == pay_type:
            filter_pay_type = " AND TP.pay_type in {0}".format(common.settings.pay_type_reversal['支付宝'])

        sql = "SELECT T.id, T.trade_time, T.profile_type, U.ico_thumbnail, T.trade_price, T.trade_number, TD.`status`, TP.pay_type " \
            "FROM common_tradediscountprofile AS TD " \
            "LEFT JOIN common_trade AS T ON TD.trade_id = T.id " \
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "WHERE T.shop_id = {0} AND T.has_pay IS TRUE AND T.settle_type != 'nothing' {1} {2} " \
            "UNION ALL " \
            "SELECT T.id, T.trade_time, 'ticket', U.ico_thumbnail, TT.trade_price, TT.ticket_number, TT.`status`, TP.pay_type " \
            "FROM common_tradeticketprofile AS TT " \
            "LEFT JOIN common_trade AS T ON TT.trade_id = T.id " \
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "WHERE T.shop_id = {0} AND T.has_pay IS TRUE {1} {2} " \
            "UNION ALL " \
            "SELECT T.id, T.trade_time, T.profile_type, U.ico_thumbnail, T.trade_price, T.trade_number, TM.`status`, TP.pay_type " \
            "FROM common_tradememberprofile AS TM " \
            "LEFT JOIN common_trade AS T ON TM.trade_id = T.id " \
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "WHERE T.shop_id = {0} AND T.has_pay IS TRUE {1} {2} " \
            "ORDER BY id DESC".format(shop_id, filter_time, filter_pay_type)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for item in fetchall:
            tmp = TradeSerializer()
            tmp.time = timetuple_utc(item[1])
            tmp.type = item[2]
            tmp.buyer_ico = GetAbsoluteImageUrl(request, item[3])
            tmp.total_fee = decimal2string(item[4])
            tmp.number = item[5]
            if 'refund' == item[6]:
                tmp.remark = '(已退款)'

            tmp.pay_type = my_settings.PAY_TYPE_DICT[item[7]] if item[7] else ''

            serializers.append(tmp)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(serializers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class TradeDiscountViewSet(mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeDiscountProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeDiscountSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeDiscountProfile.objects.get(trade__shop_id=kwargs['pk_shop'], trade__trade_number=kwargs['pk'])
        except TradeDiscountProfile.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def refund(self, request, pk_shop, pk):
        try:
            instance = TradeDiscountProfile.objects.get(trade__shop_id=pk_shop, trade__trade_number=pk)
        except TradeDiscountProfile.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        if instance.status != 'pay':
            raise ValidationDict211Error('error')

        Refund().auto(instance.trade.trade_number, 'seller doubt')

        return Response({'detail': 'OK'})

class TradeTicketViewSet(mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeTicketProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeTicketSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeTicketProfile.objects.get(trade__shop_id=kwargs['pk_shop'], ticket_number=kwargs['pk'])
        except TradeTicketProfile.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeMemberViewSet(mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeMemberProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeMemberSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeMemberProfile.objects.get(trade__shop_id=kwargs['pk_shop'], trade__trade_number=kwargs['pk'])
        except TradeMemberProfile.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeExperienceViewSet(mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeExperienceProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeExperienceSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeExperienceProfile.objects.get(trade__shop_id=kwargs['pk_shop'], ticket__ticket_number=kwargs['pk'])
        except TradeExperienceProfile.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeRefundViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = TradeRecord.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        shop_id = kwargs['pk_shop']

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter_time = " AND TR.refund_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        sql = "SELECT TR.id, TR.refund_time, T.profile_type, U.ico_thumbnail, TR.amount, T.trade_number, TP.pay_type " \
            "FROM common_traderefund AS TR " \
            "LEFT JOIN common_trade AS T ON TR.trade_id = T.id " \
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "WHERE T.shop_id = {0} AND T.profile_type = 'discount' {1} " \
            "UNION ALL " \
            "SELECT TR.id, TR.refund_time, T.profile_type, U.ico_thumbnail, TR.amount, TT.ticket_number, TP.pay_type " \
            "FROM common_traderefund AS TR " \
            "LEFT JOIN common_trade AS T ON TR.trade_id = T.id " \
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "LEFT JOIN common_tradeticketprofile AS TT ON T.id = TT.trade_id " \
            "WHERE T.shop_id = {0} AND T.profile_type = 'ticket' {1} " \
            "ORDER BY id DESC ".format(shop_id, filter_time)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for item in fetchall:
            tmp = TradeSerializer()
            tmp.time = timetuple_utc(item[1])
            tmp.type = item[2]
            tmp.buyer_ico = GetAbsoluteImageUrl(request, item[3])
            tmp.total_fee = decimal2string(item[4])
            tmp.number = item[5]
            tmp.pay_type = my_settings.PAY_TYPE_DICT[item[6]] if item[6] else ''

            serializers.append(tmp)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(serializers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class TradeShopViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeShop.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeShopSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter = Q(shop_id=kwargs['pk_shop']) & Q(has_pay=True) \
                 & Q(trade_time__gte=begin_time) & Q(trade_time__lt=endtime)

        queryset = TradeShop.objects.filter(filter).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeShop.objects.get(trade_number=kwargs['pk'], shop_id=kwargs['pk_shop'])
        except TradeShop.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeBonusViewSet(mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    queryset = TradeShop.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = TradeBonusSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        shop_id = kwargs['pk_shop']

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']

        filter_time = " AND T.trade_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        sql = "SELECT T.id, T.trade_time, T.profile_type, U.ico_thumbnail, TD.brokerage, T.trade_number "\
            "FROM common_tradediscountprofile AS TD "\
            "LEFT JOIN common_trade AS T ON TD.trade_id = T.id "\
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id "\
            "WHERE TD.`status` = 'confirm' AND TD.brokerage > 0 AND T.shop_id = {0} {1} "\
            "ORDER BY T.id DESC ".format(shop_id, filter_time)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for item in fetchall:
            tmp = self.serializer_class()
            tmp.time = timetuple_utc(item[1])
            tmp.type = item[2]
            tmp.buyer_ico = GetAbsoluteImageUrl(request, item[3])
            tmp.brokerage = decimal2string(item[4])
            tmp.number = item[5]

            serializers.append(tmp)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(serializers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class CashRecordViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    queryset = ShopCashRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = CashRecordSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter = Q(shop_id=kwargs['pk_shop']) & Q(bank_time__gte=begin_time) & Q(bank_time__lt=endtime)

        queryset = ShopCashRecord.objects.filter(filter).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CashRecordListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = CashRecordListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = ShopCashRecord.objects.get(pk=kwargs['pk'])
        except Trade.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class FlyerViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = ShopFlyer.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopFlyerSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopFlyer.objects.filter(shop_id=kwargs['pk_shop'], status= 'online').order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    @list_route(methods=['get'])
    def nearby(self, request, *args, **kwargs):
        list_geo = RedisIF.r.georadiusbymember('ShopGeo', int(kwargs['pk_shop']), 2000, unit="m", withdist=True, sort='ASC')
        map_geo = {int(list_geo[i][0]): list_geo[i][1] for i in range(0, len(list_geo), 1)}
        del map_geo[int(kwargs['pk_shop'])]

        serializer = FlyerFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter = Q(shop_id__in=map_geo.keys()) & Q(status__in=('online', 'limit'))

        type = None

        if 'shop_type' in serializer.data:
            type = serializer.data['shop_type']
        elif 'type' in serializer.data:
            type = serializer.data['type']

        if type and type != 10:
            filter = filter & Q(shop__type_id=type)

        if 'name' in serializer.data:
            filter = filter & Q(shop__name__contains=serializer.data['name'])

        queryset = ShopFlyer.objects.filter(filter).order_by('-id')
        tmp = set(item.shop_id for item in queryset)
        queryset2 = Flyer2Shop.objects.filter(shop_id=kwargs['pk_shop'], flyer__shop_id__in=tmp)
        tmp2 = {item.flyer_id:item.id for item in queryset2}
        for item in queryset:
            item.distance = map_geo[item.shop_id]
            item.league = item.id in tmp2.keys()
            if item.league:
                item.league_id = tmp2[item.id]

        queryset = sorted(queryset, key=lambda query: (query.distance))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ShopFlyerNearbySerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ShopFlyerNearbySerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    @detail_route(methods=['post'])
    def offline(self, request, pk_shop, pk):
        ShopFlyer.objects.filter(pk=pk, shop_id=pk_shop).update(status='invalid')
        Flyer2Shop.objects.filter(flyer_id=pk).delete()

        return Response({'detail': 'OK'})

    @list_route(methods=['post'])
    def spoke(self, request, *args, **kwargs):
        flyer_id = request.data['flyer_id']
        try:
            flyer = ShopFlyer.objects.get(pk=flyer_id, status='online')
        except ShopFlyer.DoesNotExist:
            raise ValidationDict211Error('暂时无法联盟')

        if Flyer2Shop.objects.filter(flyer__shop=flyer.shop).count() >= 20:
            raise ValidationDict211Error('对方店铺到达上限')

        if Flyer2Shop.objects.filter(shop_id=kwargs['pk_shop']).count() >= 2:
            raise ValidationDict211Error('主动联盟到达上限')

        Flyer2Shop.objects.create(shop_id=kwargs['pk_shop'], flyer_id=flyer_id)
        Shop.objects.filter(pk=flyer.shop.id).update(league_count=F('league_count')+1)

        return Response({'detail': 'OK'})

class FlyerProfileViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated,]

    @shop_manage
    def create(self, request, *args, **kwargs):
        if ShopWallet.objects.get(pk=kwargs['pk_shop']).bonus_pool <= 0:
            raise ValidationDict211Error('奖金池已无奖金')

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(shop_id=kwargs['pk_shop'])

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.model_class.objects.get(pk=kwargs['pk'])
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['patch'])
    @shop_manage
    def modify(self, request, pk_shop, pk):
        profile = self.model_class.objects.get(pk=pk)
        flyer = profile.flyer
        serializer = ShopFlyerProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if flyer.status != 'online':
            raise ValidationDict211Error('没有权限')

        old_id = flyer.id
        flyer.left_time = timezone.now()
        flyer.status = 'invalid'
        flyer.save(update_fields=['left_time', 'status'])

        flyer = {'shop':flyer.shop, 'img':flyer.img, 'bonus':flyer.bonus, 'valid_period_end':flyer.valid_period_end,
                'day_begin':flyer.day_begin, 'day_end':flyer.day_end, 'festival':flyer.festival,
                'precautions':flyer.precautions, 'tips':flyer.tips, 'type':flyer.type}

        if 'flyer' in serializer.validated_data.keys():
            flyer_input = serializer.validated_data.pop('flyer')
            for k, v in flyer_input.items():
                flyer[k] = v

        flyer = ShopFlyer.objects.create(shop_id=pk_shop, **flyer)

        Flyer2Shop.objects.filter(flyer_id=old_id).update(flyer=flyer)

        temp = {}
        if 1 == flyer.type:
            if isinstance(profile, ShopFlyerDiscountProfile):
                temp['bonus_type'] = profile.bonus_type
                temp['discount'] = profile.discount
                temp['full_price'] = profile.full_price
            for k, v in serializer.validated_data.items():
                temp[k] = v

            ShopFlyerDiscountProfile.objects.create(flyer=flyer, **temp)
        elif 2 == flyer.type:
            if isinstance(profile, ShopFlyerReduceProfile):
                temp['full_price'] = profile.full_price
                temp['reduce_price'] = profile.reduce_price
            for k, v in serializer.validated_data.items():
                temp[k] = v

            ShopFlyerReduceProfile.objects.create(flyer=flyer, **temp)
        elif 3 == flyer.type:
            if isinstance(profile, ShopFlyerExperienceProfile):
                temp['name'] = profile.name
                temp['original_price'] = profile.original_price
            goods = serializer.validated_data.pop('goods') if 'goods' in serializer.validated_data.keys() else []
            for k, v in serializer.validated_data.items():
                temp[k] = v

            profile = ShopFlyerExperienceProfile.objects.create(flyer=flyer, **temp)
            if not goods:
                flyer = ShopFlyerExperienceGoods.objects.filter(combo_id=pk)

                for item in flyer:
                    ectype = item.__dict__.copy()
                    del ectype['_state']
                    del ectype['id']
                    del ectype['combo_id']
                    goods.append(ectype)

            ShopFlyerExperienceGoods.objects.bulk_create(
                [ShopFlyerExperienceGoods(combo=profile, **item) for item in goods])

        return Response({'detail': 'OK'})

class FlyerDiscountViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerDiscountProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerDiscountSerializer

    pass

class FlyerReduceViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerReduceProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerReduceSerializer

    pass

class FlyerExperienceViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerExperienceProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerExperienceSerializer

    pass

class Flyer2ShopMineViewSet(mixins.ListModelMixin,
                            mixins.DestroyModelMixin,
                            viewsets.GenericViewSet):
    queryset = Flyer2Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = Flyer2ShopMineSerializer

    def list(self, request, *args, **kwargs):
        queryset = Flyer2Shop.objects.filter(flyer__status__in=('online', 'limit'), flyer__shop=kwargs['pk_shop'])
        shop = Shop.objects.get(pk=kwargs['pk_shop'])
        shops = Shop.objects.filter(pk__in=[item.shop_id for item in queryset])

        shops_distance = {}
        for item in shops:
            shops_distance[item.id] = calcDistance(shop.latitude, shop.longitude, item.latitude, item.longitude)

        for item in queryset:
            item.distance = shops_distance[item.shop_id]

        #queryset = queryset.order_by('distance')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def destroy(self, request, *args, **kwargs):
        return super(Flyer2ShopMineViewSet, self).destroy(request, *args, **kwargs)

class Flyer2ShopOtherViewSet(mixins.ListModelMixin,
                             mixins.DestroyModelMixin,
                             viewsets.GenericViewSet):
    queryset = Flyer2Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = Flyer2ShopOhterSerializer

    def list(self, request, *args, **kwargs):
        queryset = Flyer2Shop.objects.filter(shop_id=kwargs['pk_shop'])

        shop = Shop.objects.get(pk=kwargs['pk_shop'])
        shops = Shop.objects.filter(pk__in=[item.flyer.shop_id for item in queryset])

        shops_distance = {item.id:calcDistance(shop.latitude, shop.longitude, item.latitude, item.longitude) for item in shops}

        temp = []
        for item in queryset:
            item.flyer.temp = item.id
            item.flyer.distance = shops_distance[item.flyer.shop_id]
            temp.append(item.flyer)

        queryset = sorted(temp, key=lambda query: (query.distance))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def destroy(self, request, *args, **kwargs):
        return super(Flyer2ShopOtherViewSet, self).destroy(request, *args, **kwargs)

class FlyerTradeMineViewSet(mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = TradeDiscountProfile.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = FlyerTradeMineSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter_time = " AND T.trade_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        sql = "SELECT T.id, FU.ticket_number, 0, F.type, F.bonus, T.profile_type, T.trade_time, U.nick_name, U.ico_thumbnail, S.name, S.ico_thumbnail " \
              "FROM common_tradeexperienceprofile AS TE " \
              "LEFT JOIN common_trade AS T ON TE.trade_id = T.id " \
              "LEFT JOIN common_flyer2user AS FU ON TE.ticket_id = FU.id " \
              "LEFT JOIN common_shopflyer AS F ON FU.flyer_id = F.id " \
              "LEFT JOIN common_shop AS S ON FU.shop_id = S.id " \
              "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
              "WHERE T.shop_id = {0} {1} AND T.has_pay = TRUE " \
              "UNION ALL " \
              "SELECT T.id, T.trade_number, T.trade_price, F.type, F.bonus, T.profile_type, T.trade_time, U.nick_name, U.ico_thumbnail, S.name, S.ico_thumbnail " \
              "FROM common_tradediscountprofile AS TD " \
              "LEFT JOIN common_trade AS T ON TD.trade_id = T.id " \
              "LEFT JOIN common_flyer2user AS FU ON TD.ticket_id = FU.id " \
              "LEFT JOIN common_shopflyer AS F ON FU.flyer_id = F.id " \
              "LEFT JOIN common_shop AS S ON FU.shop_id = S.id " \
              "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
              "WHERE T.shop_id = {0} {1} AND T.has_pay = TRUE AND TD.ticket_id IS NOT NULL " \
              "ORDER BY id DESC ".format(int(kwargs['pk_shop']), filter_time)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        queryset = []

        for obj in fetchall:
            serializer = self.serializer_class()
            serializer.number = obj[1]
            serializer.trade_price = obj[2]
            serializer.type = obj[3]
            serializer.bonus = obj[4]
            serializer.trade_type = obj[5]
            serializer.time = timetuple_utc(obj[6])
            serializer.buyer_name = obj[7]
            serializer.buyer_ico = GetAbsoluteImageUrl(request, obj[8])
            serializer.shop_name = obj[9]
            serializer.shop_ico = GetAbsoluteImageUrl(request, obj[10])

            queryset.append(serializer)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class FlyerTradeOtherViewSet(mixins.ListModelMixin,
                             viewsets.GenericViewSet):
    queryset = TradeDiscountProfile.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = FlyerTradeOtherSerializer

    def list(self, request, *args, **kwargs):
        serializer = TradeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        begin_time = serializer.validated_data['begin_time']
        endtime = serializer.validated_data['end_time']
        filter_time = " AND T.trade_time BETWEEN '{0}' AND '{1}'".format(begin_time, endtime)

        sql = "SELECT T.id, F.type, F.bonus, T.profile_type, T.trade_time, U.nick_name, U.ico_thumbnail, S.name, S.ico_thumbnail "\
            "FROM common_tradeexperienceprofile AS TE "\
            "LEFT JOIN common_trade AS T ON TE.trade_id = T.id "\
            "LEFT JOIN common_flyer2user AS FU ON TE.ticket_id = FU.id "\
            "LEFT JOIN common_shopflyer AS F ON FU.flyer_id = F.id "\
            "LEFT JOIN common_shop AS S ON T.shop_id = S.id "\
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id " \
            "WHERE FU.shop_id = {0} {1} AND T.has_pay = TRUE AND FU.`status` = 'settled' " \
            "UNION ALL "\
            "SELECT T.id, F.type, F.bonus, T.profile_type, T.trade_time, U.nick_name, U.ico_thumbnail, S.name, S.ico_thumbnail "\
            "FROM common_tradediscountprofile AS TD "\
            "LEFT JOIN common_trade AS T ON TD.trade_id = T.id "\
            "LEFT JOIN common_flyer2user AS FU ON TD.ticket_id = FU.id "\
            "LEFT JOIN common_shopflyer AS F ON FU.flyer_id = F.id "\
            "LEFT JOIN common_shop AS S ON T.shop_id = S.id "\
            "LEFT JOIN common_myuser AS U ON T.buyer_id = U.id "\
            "WHERE FU.shop_id = {0} {1} AND T.has_pay = TRUE AND FU.`status` = 'settled' AND TD.ticket_id IS NOT NULL "\
            "ORDER BY id DESC ".format(int(kwargs['pk_shop']), filter_time)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        queryset = []

        for obj in fetchall:
            serializer = self.serializer_class()
            serializer.type = obj[1]
            serializer.bonus = obj[2]
            serializer.trade_type = obj[3]
            serializer.time = timetuple_utc(obj[4])
            serializer.buyer_name = obj[5]
            serializer.buyer_ico = GetAbsoluteImageUrl(request, obj[6])
            serializer.shop_name = obj[7]
            serializer.shop_ico = GetAbsoluteImageUrl(request, obj[8])

            queryset.append(serializer)

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class ShopManagerViewSet(mixins.ListModelMixin,
                         mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsSeller]
    serializer_class = ShopManagerSerializer

    def list(self, request, *args, **kwargs):
        queryset = Shop.objects.get(pk=kwargs['pk_shop']).shopmanagership_set.all()

        return response_list(self, self.serializer_class, queryset)

    def create(self, request, *args, **kwargs):
        serializer = ShopManagerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(shop_id=kwargs['pk_shop'])
        return Response({'detail': 'OK'})

    def destroy(self, request, *args, **kwargs):
        obj = ShopManagerShip.objects.get(user_id=kwargs['pk'], shop_id=kwargs['pk_shop'])

        if Shop.objects.get(pk=kwargs['pk_shop']).seller_id == obj.user_id:
            raise ValidationDict211Error('不能取消自己的管理员身份')

        obj.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

class ShopPhotoViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopPhoto.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsManager]
    serializer_class = ShopPhotoSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopPhoto.objects.filter(Q(shop__managers=request.user) & Q(shop_id=kwargs['pk_shop']))
        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results':serializer.data})

    @list_route(methods=['post'])
    def add_photos(self, request, *args, **kwargs):
        serializer = ShopPhotoAddListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['shop'] = Shop.objects.get(pk=kwargs['pk_shop'])
        serializer.save(serializer.validated_data)
        return Response({'detail': 'OK'})

    @list_route(methods=['post'])
    def del_photos(self, request, *args, **kwargs):
        serializer = DelIDsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ShopPhoto.objects.filter(shop_id=kwargs['pk_shop'], pk__in=serializer.validated_data['ids']).delete()
        return Response({'detail': 'OK'})
