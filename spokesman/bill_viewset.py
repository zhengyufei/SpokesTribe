import decimal

from django.db.models import Q
from rest_framework import viewsets, permissions, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

import SpokesTribe.settings as settings
from Logger.logger import Logger
from MyAbstract.exceptions import ValidationDict211Error
from Pay.Ali import alipay
from Pay.Integrated.Zhaoshang import ZhaoBank
from Pay.Integrated.Fuyou import FuyouPay
from Pay.Weixin import weixinpay
from RedisIF.shop import Shop as redis_shop
from common.models import Trade, TradeTicketProfile, TradeRecord, TradeRefund, CashRecord, ShopMember, TradePay
from common.refund import Refund
from common.serializers import TradePayResponseSerializer
from .serializers import TradeBuyerSerializer, TradeBuyerListSerializer, TradeSpokesmanSerializer, \
    CommentCreateSerializer, TradeTicketProfileSerializer, RefundTicketSerializer, \
    TradeRefundListSerializer, TradeRefundSerializer, TradeAvailableSerializer, CashRecordListSerializer, \
    CashRecordSerializer, PaySerializer, TradeIntroSerializer, BuyerFilterSerializer


class TradeBuyerViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = Trade.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = TradeBuyerSerializer

    def list(self, request, *args, **kwargs):
        serializer = BuyerFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        queryset = Trade.objects.filter(buyer=request.user, has_pay=True, profile_type=serializer.validated_data['type']).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = TradeBuyerListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = TradeBuyerListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = Trade.objects.get(buyer=request.user, trade_number=kwargs['pk'])
        except Trade.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['get'])
    def intro(self, request, pk=None):
        serializer = TradeIntroSerializer()

        try:
            trade = Trade.objects.get(trade_number=pk, buyer=request.user)
            serializer.shop_id = trade.shop_id
            serializer.spoker_id = trade.spokesman_id
            serializer.has_pay = trade.has_pay
            serializer.amount = trade.trade_price
            serializer.discount = trade.total_fee - trade.trade_price

        except Trade.DoesNotExist:
            raise ValidationDict211Error('订单号错误')

        serializer = TradeIntroSerializer(serializer)
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def pay(self, request, pk=None):
        # 1 weixin 2 zhifubao 3 weixin_pa 4 zhaoshang 5 member 6 zhaobank_weixin 7 zhaobank_ali 8fuyou_weixinjs 9 fuyou_zhifubaojs
        if not settings.ONLINE:
            raise ValidationDict211Error('pay only online')

        serializer = PaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pay_type = serializer.validated_data['pay_type']
            pay_password = serializer.validated_data['pay_password'] if 'pay_password' in serializer.validated_data else None
            fy_wx_openid = serializer.validated_data['fy_wx_openid'] if 'fy_wx_openid' in serializer.validated_data else None
            serializer = None
            trade = Trade.objects.get(trade_number=pk, buyer=request.user)

            if trade.has_pay:
                raise ValidationDict211Error('payed')

            trade_price = trade.trade_price
            if pay_password and pay_type != 5 and trade.shop.combo_pay:
                if trade.profile_type in ('ticket', 'member'):
                    raise ValidationDict211Error('不支持')
                member = ShopMember.objects.get(shop=trade.shop, user=request.user)
                trade_price = trade_price - member.loose_change

                self.member(trade, member.loose_change, pay_password, True)

            if pay_type == 1:
                serializer = self.weixin(trade, trade_price)
            elif pay_type == 2:
                serializer = self.ali(trade, trade_price)
            elif pay_type == 5:
                if trade.profile_type == 'member':
                    raise ValidationDict211Error('不支持')

                serializer = self.member(trade, trade_price, pay_password)
                trade.has_pay = True
                trade.save(update_fields=['has_pay'])
            elif pay_type in (6, 7) and trade.shop.pay_type == 1: #zhangbank + weixin or ali
                token = Token.objects.get(user=request.user)
                serializer = self.zhaobank(trade, pay_type, trade_price, token.key)
            elif pay_type in (8, 9) and trade.shop.pay_type == 2:
                serializer = self.fuyou(trade, pay_type, trade_price, request.user, fy_wx_openid)

            trade.set_settle_type()

        except Trade.DoesNotExist:
            raise ValidationDict211Error('no')

        if not serializer:
            raise ValidationDict211Error('not find trade')

        serializer = TradePayResponseSerializer(serializer)
        return Response(serializer.data)

    def weixin(self, trade, price):
        n_charge_ratio = int(redis_shop.get_charge_ratio(trade.shop.id))
        TradePay.objects.create(trade=trade, trade_price=price, charge_ratio=n_charge_ratio, pay_type='weixin')

        serializer = TradePayResponseSerializer()
        serializer.sign = weixinpay.BuyerPay().pay_sign(trade.id, trade.trade_number, price)

        return serializer

    def ali(self, trade, price):
        n_charge_ratio = int(redis_shop.get_charge_ratio(trade.shop.id))
        TradePay.objects.create(trade=trade, trade_price=price, charge_ratio=n_charge_ratio, pay_type='ali')

        serializer = TradePayResponseSerializer()
        serializer.sign = alipay.BuyerPay().pay_sign(trade.id, trade.trade_number, price)

        return serializer

    def zhaobank(self, trade, type, price, token):
        if trade.shop.zhaoshang.type == 'shop':
            open_id = trade.shop.zhaoshang.open_id
            open_key = trade.shop.zhaoshang.open_key
        else:
            open_id = ZhaoBank.PayConf.mine_open_id
            open_key = ZhaoBank.PayConf.mine_open_key

        #discount comment
        jump = 'discount' if 'discount' == trade.profile_type else 'other'
        pay = ZhaoBank.Pay(open_id, open_key, trade.trade_number, type, price, token, jump,
                           shop_id=trade.shop_id, spoker_id=trade.spokesman_id)
        res = pay.getResponse()
        # same as TradePay
        pay_type = 'zb_wx' if type == 6 else 'zb_ali'
        n_charge_ratio = int(redis_shop.get_charge_ratio(trade.shop.id))
        TradePay.objects.create(trade=trade, trade_price=price, charge_ratio=n_charge_ratio, pay_type=pay_type,
            zhaobank_no=res['ord_no'])

        serializer = TradePayResponseSerializer()
        serializer.url = res['jsapi_pay_url']
        serializer.type = type

        return serializer

    def fuyou(self, trade, type, price, user, fy_wx_openid):
        fuyou = trade.shop.fuyou

        if type == 8:
            third = user.get_third()
            if not fy_wx_openid:
                if not fuyou.is_wx_oasis:
                    fy_wx_openid = third.fy_wx_openid
                else:
                    fy_wx_openid = third.fy_wx_oasis_openid

                if not fy_wx_openid:
                    raise ValidationDict211Error('missing openid')
            else:
                if not fuyou.is_wx_oasis:
                    third.fy_wx_openid = fy_wx_openid
                    third.save(update_fields=['fy_wx_openid'])
                else:
                    third.fy_wx_oasis_openid = fy_wx_openid
                    third.save(update_fields=['fy_wx_oasis_openid'])

            temp = FuyouPay.JsPay(fuyou.merchant_no, fuyou.terminal_id, fuyou.access_token,
                                  trade.shop.name,
                                  trade.trade_number, FuyouPay.PayConf.weixin_type, price,
                                  fy_wx_openid, FuyouPay.PayConf.get_notify_url(trade.trade_number))
            result = temp.getResponse()
            print('test1', result)
            serializer = TradePayResponseSerializer()
            serializer.type = type
            serializer.sign = temp.tempFunc(result['appId'], result['timeStamp'], result['nonceStr'],
                                            result['package_str'], result['signType'], result['paySign'])
        else:
            temp = FuyouPay.JsPay(fuyou.merchant_no, fuyou.terminal_id, fuyou.access_token,
                                  trade.shop.name,
                                  trade.trade_number, FuyouPay.PayConf.ali_type, price,
                                  user.third.zhifubao_unionid, FuyouPay.PayConf.get_notify_url(trade.trade_number))
            result = temp.getResponse()
            serializer = TradePayResponseSerializer()
            serializer.type = type
            serializer.ali_trade_no = result['ali_trade_no']

        pay_type = 'fy_wxjs' if type == 8 else 'fy_alijs'
        n_charge_ratio = int(redis_shop.get_charge_ratio(trade.shop.id))
        TradePay.objects.create(trade=trade, trade_price=price, charge_ratio=n_charge_ratio, pay_type=pay_type)

        return serializer

    def member(self, trade, price, pay_password, wait=None):
        from .function import member_pay
        from MyAbstract.funtions import decimal2string
        remain = member_pay(pay_password, trade, price, wait)

        serializer = TradePayResponseSerializer()
        serializer.remain = decimal2string(remain)

        return serializer

    @detail_route(methods=['post'])
    def comment(self, request, pk=None):
        trade = Trade.objects.get(trade_number=pk, buyer=request.user)

        allow = True

        if trade.profile_type == 'ticket':
            allow = False
            for item in TradeTicketProfile.objects.filter(trade=trade):
                if item.status == 'confirm':
                    allow = True
                    break

        if not allow:
            raise ValidationDict211Error('未使用不能评论', 'no comment')

        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trade.grade = serializer.validated_data['grade']
        trade.save(update_fields=['grade'])
        try:
            serializer.save(user=request.user, trade=trade)
        except Exception as e:
            Logger.Log('error', str(e))

        trade.shop.comment_count += 1
        trade.shop.level = (trade.shop.level * trade.shop.comment_count + trade.grade) \
                           / decimal.Decimal(trade.shop.comment_count + 1)
        trade.shop.save(update_fields=['comment_count', 'level'])

        trade.spokesman.spoke_profile.comment_count += 1
        trade.spokesman.spoke_profile.level = \
            (trade.spokesman.spoke_profile.level * trade.spokesman.spoke_profile.comment_count + trade.grade) \
            / decimal.Decimal(trade.spokesman.spoke_profile.comment_count + 1)
        trade.spokesman.spoke_profile.save(update_fields=['comment_count', 'level'])

        return Response({'result': 'OK'})

    @detail_route(methods=['get'])
    def query_combos(self, request, pk=None):
        trade = Trade.objects.get(trade_number=pk, buyer=request.user)

        serializer = TradeTicketProfileSerializer(trade.tickets.all(), many=True)

        return Response({'results': serializer.data})

    @detail_route(methods=['post'])
    def refund_combos(self, request, pk=None):
        serializer = RefundTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refund = Refund().auto_ticket(pk, serializer.validated_data['count'], serializer.validated_data['reason'])

        return Response({'id': refund.id})

    @list_route(methods=['get'])
    def available_tickets(self, request):
        queryset = TradeTicketProfile.objects.filter(trade__buyer=request.user, status='pay')

        ids = set()
        serializers = []

        for item in queryset:
            if item.trade.id in ids:
                continue

            ids.add(item.trade.id)
            # item.trade.tickets.set(item.trade.tickets.filter(status='pay'))
            item.trade.temp = item.trade.tickets.filter(status='pay')

            serializers.append(item.trade)

        queryset = serializers

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = TradeAvailableSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = TradeAvailableSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class TradeSpokesmanViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    queryset = TradeRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = TradeSpokesmanSerializer

    def list(self, request, *args, **kwargs):
        queryset = TradeRecord.objects.filter((Q(trade__spokesman=request.user) |Q(ticket__trade__spokesman=request.user))
            &((Q(ticket=None)&~Q(trade__tradediscountprofile__brokerage=0))
            |(Q(trade=None)&~Q(ticket__brokerage=0)))).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeRecord.objects.get(Q(pk=kwargs['pk'])
                & (Q(trade__spokesman=request.user) | Q(ticket__trade__spokesman=request.user)))
        except Trade.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class TradeRefundViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    queryset = TradeRefund.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = TradeRefundSerializer

    def list(self, request, *args, **kwargs):
        queryset = TradeRefund.objects.filter(trade__buyer=request.user).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = TradeRefundListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = TradeRefundListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = TradeRefund.objects.get(pk=kwargs['pk'])
        except Trade.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class CashRecordViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    queryset = CashRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = CashRecordSerializer

    def list(self, request, *args, **kwargs):
        queryset = CashRecord.objects.filter(user=request.user).order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CashRecordListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = CashRecordListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = CashRecord.objects.get(pk=kwargs['pk'])
        except Trade.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

