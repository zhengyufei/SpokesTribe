import datetime
import json

from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from APNS import apns_push
from APNS.apns_push import handle_seller_cash
from Logger.logger import Logger
from MyAbstract.exceptions import ValidationDict211Error
from Pay.Ali import alipay
from Pay.Integrated.Zhaoshang import ZhaoBank
from Pay.Integrated.Fuyou import FuyouPay
from Pay.Weixin import weixinpay
from Pay.Zhaoshang import ZhaoshangTransfer
from .models import Trade, TradeRecord, CashRecord, ShopCashRecord, Wallet, ShopWallet, ShopMember, ShopSpoke, \
    FriendGroup, ShopSpokeGroup, ShopSpokeRequest, ShopSpokeRequestHistory, TradeShop, TradeMemberProfile, \
    ShopFlyer, Flyer2User, ShopWithdrawRecord
from .serializers import FeedbackSerializer


class PayCallbackViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all()
    permission_classes = [permissions.AllowAny, ]
    serializer_class = FeedbackSerializer #unuse

    def member_create(self, trade):
        try:
            member = ShopMember.objects.create(user=trade.buyer, shop=trade.shop, phone=trade.buyer.phone_number,
                member_card=trade.member.recharge.member_card, name=trade.buyer.nick_name, loose_change=trade.total_fee)
        except:
            raise ValidationDict211Error('会员已存在')

        #existing spoker are coverded into members
        if ShopSpoke.objects.filter(shop_id=trade.shop.id, spokesman=trade.buyer).exists():
            ShopSpoke.objects.filter(shop_id=trade.shop.id, spokesman=trade.buyer).update(spokesman_id=None, member=member, type='member')
        else:
            try:
                #delete existing request
                obj = ShopSpokeRequest.objects.get(spokesman=trade.buyer, shop_id=trade.shop.id)
                ShopSpokeRequestHistory.objects.create(shop=obj.shop, spokesman=obj.resume.user,
                    request_time=obj.request_time, result=False)
                obj.delete()
            except:
                pass

            # todo
            ShopSpoke.objects.create(shop_id=trade.shop.id, member=member, type='member')
            group = FriendGroup.objects.get(user=trade.buyer, type=3)
            discount = member.member_card.discount.discount if hasattr(member.member_card, 'discount') else 100
            ShopSpokeGroup.objects.create(shop_id=trade.shop.id, group=group, discount=(0.5 * discount + 50),
                 member_discount=(0.5 * discount + 50))

    def pay_member(self, trade):
        try:
            member = ShopMember.objects.select_for_update().get(shop=trade.shop, user=trade.buyer)
            member.loose_change += trade.total_fee
            if member.member_card.level < trade.member.recharge.member_card.level:
                member.member_card = trade.member.recharge.member_card
            member.save(update_fields=['loose_change', 'member_card'])
        except ShopMember.DoesNotExist:
            self.member_create(trade)

    def brokerage(self, trade, profile):
        profile.set_status('pay', True)
        pay_type_set = trade.pay_type()

        if 'member' in pay_type_set or 'offline' in pay_type_set:
            return
        if 'weixin' in pay_type_set or 'ali' in pay_type_set:
            if profile.shop_earning > 0:
                ShopWallet.income_pay(trade.shop_id, profile.shop_earning)
            if not isinstance(profile, TradeMemberProfile) and profile.brokerage > 0:
                Wallet.income_pay(trade.spokesman_id, profile.brokerage)
        elif 'zb_wx' in pay_type_set or 'zb_ali' in pay_type_set\
                or 'fy_wxjs' in pay_type_set or 'fy_alijs' in pay_type_set:
            if profile.shop_earning > 0:
                ShopWallet.income_collect(trade.shop_id, profile.shop_earning)

            if 'pay' == profile.trade.settle_type:
                if not isinstance(profile, TradeMemberProfile) and profile.brokerage > 0:
                    Wallet.income_pay(trade.spokesman_id, profile.brokerage)

    def bonus(self, total, ticket):
        temp = ((ticket.flyer.type == 1 and ticket.flyer.discount.full_price <= total)
            or (ticket.flyer.type == 2 and ticket.flyer.reduce.full_price <= total)
            or ticket.flyer.type == 3)
        ticket.status = 'used'
        wallet = ShopWallet.objects.select_for_update().get(shop=ticket.flyer.shop)

        if ticket.flyer.type == 1 and ticket.flyer.discount.bonus_type == 2:
            bonus = total * ticket.flyer.bonus / 100
        else:
            bonus = ticket.flyer.bonus

        if wallet.bonus_pool >= bonus:
            if temp:
                ShopWallet.income_bonus(ticket.shop.id, bonus)
            ticket.status = 'settled'
        else:
            queryset = ShopFlyer.objects.filter(shop=ticket.flyer.shop, status='online')
            queryset.update(status='limit', left_time=timezone.now())

        if temp:
            wallet.bonus_pool -= bonus
            wallet.save(update_fields=['bonus_pool'])

        ticket.bonus = bonus
        ticket.save(update_fields=['status', 'bonus'])

    def pay(self, trade_number, info, fy_trade_no=None):
        trade = Trade.objects.get(trade_number=trade_number)

        if trade.has_pay or not trade.pay_back(True, info, fy_trade_no):
            return False

        if trade.profile_type not in ('discount', 'member'):
            return True

        if trade.profile_type == 'discount':
            profile = trade.tradediscountprofile
            if profile.ticket:
                self.bonus(profile.trade_price, profile.ticket)

            record = TradeRecord.objects.create(trade=trade)
            apns_push.handle_trade_success(record)

        elif trade.profile_type == 'member':
            profile = trade.member
            self.pay_member(trade)

            record = TradeRecord.objects.get_or_create(trade=trade)[0]
            apns_push.handle_trade_member_recharge(record)

        self.brokerage(trade, profile)

        return True

    @detail_route(methods=['post'])
    def weixinpay(self, request, pk=None):
        callback = weixinpay.BuyerPay().pay_callback(request.body)

        if callback.is_success() and not self.pay(callback.get_number(), callback.get_data()):
            response = '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
        else:
            response = callback.get_response()

        return Response(response)

    @detail_route(methods=['post'])
    def alipay(self, request, pk=None):
        callback = alipay.BuyerPay().pay_callback(request.POST)

        if callback.is_success():
            self.pay(callback.get_number(), callback.get_data())

        return Response('success')

    @detail_route(methods=['get'])
    def zhaobankpay(self, request, pk=None):
        callback = ZhaoBank.CallBack(request.query_params)
        if not callback.CheckSign():
            raise ValidationDict211Error('error')

        data = callback.data
        if data['status'] == '1':
            trade_number = data['out_no']
            self.pay(trade_number, json.dumps(data))

        return Response('notify_success')

    @detail_route(methods=['post'])
    def fuyoupay(self, request, pk=None):
        data = json.loads(str(request.body, encoding = "utf-8"))

        temp = data['return_code'] and data['result_code']
        if temp:
            self.pay(pk, json.dumps(data), data['out_trade_no'])

        return Response({'return_code': '01' if temp else '02', 'return_msg':''})

    @list_route(methods=['post'])
    def zhaoshangtransfer(self, request):
        data = request.POST

        Logger.Log('info', 'screen zhaoshangtransfer {0}'.format(data))
        callback = ZhaoshangTransfer.PayCallback(data)
        callback.CheckSign()
        busdat = callback.ParseBUSDAT()
        Logger.Log('info', busdat)
        status = 'success' if 'CMBMB99' == busdat['bank_code'] else 'fail'
        number = busdat['merch_serial']

        Logger.Log('info', status)
        Logger.Log('info', number)

        if 'PERSON' == number[0:6]:
            Logger.Log('info', 'PERSON')
            CashRecord.objects.filter(number=number, status='apply').update(bank_msg=busdat['bank_msg'],
                bank_code=busdat['bank_code'], status=status, bank_time=datetime.datetime.now())
        elif 'Shop' == number[0:4]:
            Logger.Log('info', 'Shop')
            ShopCashRecord.objects.filter(number=number, status='apply').update(bank_msg=busdat['bank_msg'],
                bank_code=busdat['bank_code'], status=status, bank_time=datetime.datetime.now())
        elif 'SW' == number[0:2]:
            Logger.Log('info', 'SW')
            ShopWithdrawRecord.objects.filter(number=number, status='apply').update(bank_msg=busdat['bank_msg'],
                bank_code=busdat['bank_code'], status=status, bank_time=datetime.datetime.now())
        else:
            Logger.Log('info', 'none')

        if status == 'fail':
            if 'PERSON' == number[0:6]:
                record = CashRecord.objects.get(number=number)
                Wallet.objects.filter(user=record.user).update(cash=F('cash')-record.cash)
            elif 'Shop' == number[0:4]:
                record = ShopCashRecord.objects.get(number=number)
                ShopWallet.objects.filter(shop=record.shop).update(income=F('income')+record.cash)
            elif 'SW' == number[0:2]:
                record = ShopWithdrawRecord.objects.get(number=number)
                ShopWallet.objects.filter(shop=record.shop).update(bonus=F('bonus') + record.cash)

            record.status = 'return'
            record.save(update_fields=['status'])

            Logger.Log('error', 'cash error {0}'.format(number))
        else:
            if 'Shop' == number[0:4]:
                record = ShopCashRecord.objects.get(number=number)
                handle_seller_cash(record)

        return Response('success')

    def shop_pay(self, trade_number, info):
        trade = TradeShop.objects.get(trade_number=trade_number)
        if trade.pay_back(True, info):
            wallet = ShopWallet.objects.select_for_update().get(shop=trade.shop)
            wallet.bonus_pool += trade.trade_price
            wallet.save(update_fields=['bonus_pool'])
            if wallet.bonus_pool > 0:
                ShopFlyer.objects.filter(shop=trade.shop, status='limit').update(status='online')
                queryset = Flyer2User.objects.filter(status='used', flyer__shop=trade.shop)

                for item in queryset:
                    ShopWallet.income_bonus(item.shop.id, item.bonus)

                queryset.update(status='settled')

    @detail_route(methods=['post'])
    def shop_weixinpay(self, request, pk=None):
        callback = weixinpay.SellerPay().pay_callback(request.body)

        if callback.is_success() and not self.shop_pay(callback.get_number(), callback.get_data()):
            response = '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
        else:
            response = callback.get_response()

        return Response(response)

    @detail_route(methods=['post'])
    def shop_alipay(self, request, pk=None):
        callback = alipay.SellerPay().pay_callback(request.POST)

        if callback.is_success():
            self.shop_pay(callback.get_number(), callback.get_data())

        return Response('success')

    @detail_route(methods=['get'])
    def shop_zhaobankpay(self, request, pk=None):
        callback = ZhaoBank.ShopCallBack(request.query_params)
        if not callback.CheckSign():
            raise ValidationDict211Error('error')

        data = callback.data

        if data['status'] == '1':
            trade_number = data['out_no']
            self.shop_pay(trade_number, json.dumps(data))

        return Response('notify_success')