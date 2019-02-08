from MyAbstract.exceptions import ValidationDict211Error
from Pay.Ali import alipay
from Pay.Integrated.Zhaoshang import ZhaoBank
from Pay.Integrated.Fuyou import FuyouPay
from Pay.Weixin import weixinpay
from common.models import ShopMember, Trade, TradeDiscountProfile, TradeTicketProfile, TradeRefund


class Refund(object):
    def auto(self, number, reason=''):
        self.refund(number, True, '13408544339', reason)

    def manual(self, number, operator, reason=''):
        self.refund(number, False, operator, reason)

    def refund(self, trade_number, auto, operator, reason):
        try:
            profile = TradeDiscountProfile.objects.get(trade__trade_number=trade_number)
            trade = profile.trade
        except:
            raise ValidationDict211Error('订单不对', detail_en='trade error')

        if trade.has_pay is True and 'pay' == profile.status:
            type = 1
        elif trade.tradepay_set.all().count() > 1:
            type = 2
        else:
            raise ValidationDict211Error('订单状态不对', detail_en='trade not allow')

        temp = 0
        for item in trade.tradepay_set.all():
            if item.pay_type == 'member':
                temp = item.trade_price
                break

        pay_type_set = trade.pay_type()
        refund_price = trade.trade_price

        if 1 == type:
            amount = refund_price
        elif 2 == type:
            amount = refund_price - temp

        refund = TradeRefund.objects.create(trade=profile.trade, amount=amount,
            auto=auto, operator=operator, reason=reason)

        profile.refund = refund
        profile.set_status('torefund')
        profile.save(update_fields=['refund', 'status'])

        if temp <= 0:
            self.outside(pay_type_set, trade_number, trade, refund_price, refund, operator)
        elif temp >= refund_price:
            if 1 == type:
                self.inside(pay_type_set, trade, refund_price, refund)
        else:
            self.outside(pay_type_set, trade_number, trade, refund_price - temp, refund, operator)
            if 1 == type:
                self.inside(pay_type_set, trade, temp, refund)

        refund.status = 'success' if refund.online_success else 'fail'
        refund.save(update_fields=['status', 'online_success', 'online_info'])
        if refund.online_success:
            profile.set_status('refund', True)

    def auto_ticket(self, number, count, reason=''):
        return self.refund_ticket(number, count, True, '13408544339', reason)

    def manual_ticket(self, number, numbers, operator, reason=''):
        return self.refund_ticket(number, numbers, False, operator, reason)

    def refund_ticket(self, trade_number, count, auto, operator, reason):
        try:
            trade = Trade.objects.get(trade_number=trade_number)
        except:
            raise ValidationDict211Error('订单不对', detail_en='trade error')

        if trade.tradepay_set.all().count() > 1:
            type = 2
        elif trade.has_pay:
            type = 1
        else:
            raise ValidationDict211Error('订单状态不对', detail_en='trade not allow')

        temp = 0
        for item in trade.tradepay_set.all():
            if item.pay_type == 'member':
                temp = item.trade_price
                break

        refund_price = trade.trade_price

        if 2 == type:
            amount = refund_price - temp

        queryset = TradeTicketProfile.objects.filter(trade__trade_number=trade_number)
        pay_count = 0
        refund_count = 0
        tickets = []
        unit_price = None
        for item in queryset:
            if not unit_price:
                unit_price = item.trade_price
            if item.status == 'pay':
                pay_count += 1
                if pay_count <= count:
                    tickets.append(item)
            elif item.status == 'refund':
                refund_count += 1

        if count > pay_count:
            raise ValidationDict211Error('数量错误', 'count is more')

        trade = Trade.objects.get(trade_number=trade_number, has_pay=True)

        member_trade_price = 0
        for item in trade.tradepay_set.all():
            if item.pay_type == 'member':
                member_trade_price = item.trade_price
                break

        pay_type_set = trade.pay_type()
        has_refund_price = unit_price * refund_count
        temp = member_trade_price - has_refund_price

        refund_price = unit_price * len(tickets)

        if 1 == type:
            amount = refund_price

        refund = TradeRefund.objects.create(trade=trade, amount=amount, auto=auto, operator=operator, reason=reason)

        for item in tickets:
            item.refund = refund
            item.set_status('torefund')
            item.save(update_fields=['refund', 'status'])

        if temp <= 0:
            self.outside(pay_type_set, trade_number, trade, refund_price, refund, operator)
        elif temp >= refund_price:
            self.inside(pay_type_set, trade, refund_price, refund)
        else:
            self.outside(pay_type_set, trade_number, trade, refund_price - temp, refund, operator)
            self.inside(pay_type_set, trade, temp, refund)

        refund.status = 'success' if refund.online_success else 'fail'
        refund.save(update_fields=['status', 'online_success', 'online_info', 'member_remain'])
        if refund.online_success:
            for item in tickets:
                item.refund = refund
                item.set_status('refund')
                item.save(update_fields=['status', 'refund'])

        return refund

    def outside(self, pay_type_set, trade_number, trade, refund_price, refund, operator):
        if 'weixin' in pay_type_set:
            response = self.weixin_refund(trade_number, trade.trade_price, refund_price, refund.refund_number, operator)
            refund.online_success, refund.online_info = self.parse_weixin_response(response)
        elif 'ali' in pay_type_set:
            response = self.ali_refund(trade_number, refund_price, refund.refund_number)
            refund.online_success, refund.online_info = self.parse_ali_response(response)
        elif 'zb_wx' in pay_type_set or 'zb_ali' in pay_type_set:
            response = self.zhaobank_refund(trade_number, refund_price, refund.refund_number)
            refund.online_success, refund.online_info = self.parse_zhaobank_response(response)
        elif 'fy_wxjs' in pay_type_set or 'fy_alijs' in pay_type_set:
            response = self.fy_refund(trade_number, refund_price, refund.refund_number)
            refund.online_success, refund.online_info = self.parse_fy_response(response)

    def inside(self, pay_type_set, trade, refund_price, refund):
        if 'member' in pay_type_set:
            member = ShopMember.objects.get(shop=trade.shop, user=trade.buyer)
            member.loose_change += refund_price
            member.save(update_fields=['loose_change'])
            refund.online_success, refund.online_info, refund.member_remain = True, 'member', member.loose_change

    def ali_refund(self, trade_number, amount, refund_number):
        response = alipay.BuyerPay().refund(trade_number, amount, refund_number)
        print(response)
        return response

    def weixin_refund(self, trade_number, total, amount, refund_number, operator):
        response = weixinpay.SellerPay().refund(trade_number, total, refund_number, amount, operator)
        print(response)
        return response

    def zhaobank_refund(self, trade_number, amount, refund_number):
        trade = Trade.objects.get(trade_number=trade_number)
        for item in trade.tradepay_set.all():
            if item.pay_type in ['zb_wx', 'zb_ali']:
                zhaobank_no = item.zhaobank_no
                break
        else:
            raise ValidationDict211Error('error')

        if trade.shop.zhaoshang.type == 'shop':
            open_id = trade.shop.zhaoshang.open_id
            open_key = trade.shop.zhaoshang.open_key
            password = trade.shop.zhaoshang.password
        else:
            open_id = ZhaoBank.PayConf.mine_open_id
            open_key = ZhaoBank.PayConf.mine_open_key
            password = ZhaoBank.PayConf.mine_password

        refund = ZhaoBank.Refund(open_id, open_key, password, trade.id, zhaobank_no, refund_number, amount)

        return refund.getResponse()

    def fy_refund(self, trade_number, amount, refund_number):
        trade = Trade.objects.get(trade_number=trade_number)
        for item in trade.tradepay_set.all():
            if item.pay_type in ['fy_wxjs', 'fy_alijs']:
                fuyou_trade_no = item.fuyou_trade_no
                pay_type = item.pay_type
                break
        else:
            raise ValidationDict211Error('error')

        fuyou = trade.shop.fuyou
        if pay_type == 'fy_wxjs':
            pay_type = FuyouPay.PayConf.weixin_type
        elif pay_type == 'fy_alijs':
            pay_type = FuyouPay.PayConf.ali_type

        refund = FuyouPay.Refund(fuyou.merchant_no, fuyou.terminal_id, fuyou.access_token, refund_number, pay_type, amount, fuyou_trade_no)

        return refund.getResponse()

    def parse_ali_response(self, response):
        if response['alipay_trade_refund_response']['code'] == '10000':
            return True, response
        else:
            return False, response

    def parse_weixin_response(self, response):
        if response['return_code'] == 'SUCCESS' and response['result_code'] == 'SUCCESS':
            return True, response
        else:
            return False, response

    def parse_zhaobank_response(self, response):
        if 'error' not in response.keys():
            return True, response
        else:
            return False, response

    def parse_fy_response(self, response):
        if response['result_code'] == '01':
            return True, response
        else:
            return False, response
