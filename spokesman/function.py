import decimal, math
from MyAbstract.funtions import fenceil, fenfloor


def calculate(price, is_valid, type=None, discount=None, full_price=None, reduce_price=None):
    if not is_valid \
        or (1==type and not discount) \
        or (2==type and not reduce_price):
        return price

    if 1 == type:
        return price * discount / decimal.Decimal(100.0)
    elif 2 == type:
        if price >= full_price:
            return price - reduce_price
        else:
            return price

    return price

def calculate_trade(price, constant, activity_is_valid, activity_type, activity_discount, activity_full, activity_reduce,
                    discount_is_valid, discount_type, discount_discount, discount_full, discount_reduce):
    trade_activity = calculate(price, activity_is_valid, activity_type, activity_discount, activity_full, activity_reduce)
    trade_activity = fenceil(trade_activity)
    trade_discount = calculate(trade_activity, discount_is_valid, discount_type, discount_discount, discount_full, discount_reduce)
    trade_discount = fenceil(trade_discount)

    return (trade_discount + constant, trade_activity)

def calculate_brokerage(price, is_valid, type, discount, full_price, reduce_price, spokesman_discount, is_brokerage):
    second = 0
    if 1 == type:
        second = calculate(price, is_valid, type, spokesman_discount, full_price, reduce_price)
    elif 2 == type:
        second = calculate(price, is_valid, type, discount, full_price, spokesman_discount)

    if not is_brokerage:
        first = calculate(price, is_valid, type, discount, full_price, reduce_price)
        return (price - second, second - first)
    else:
        return (price - second, 0)

def translate(is_valid, type, discount, full_price, reduce_price):
    if not is_valid:
        return ''

    if 1 == type:
        return '%.1f折扣' % (discount / decimal.Decimal(10.0))
    elif 2 == type:
        return '满%d减%d' % (full_price, reduce_price)

    return ''

def calculate_trade_dict(total, constant, is_activity, activity_type, activity_discount, activity_full, activity_reduce,
          is_discount, discount_type, shop_discount, shop_full, shop_reduce, spokesman_discount, is_brokerage):
    discount = total - constant

    activity_translate = ''

    if is_activity:
        activity_translate = translate(is_activity, activity_type, activity_discount, activity_full, activity_reduce)

    if not spokesman_discount:
        if 1 == discount_type:
            spokesman_discount = 100
        elif 2 == discount_type:
            spokesman_discount = 0

    shop_discount_translate = ''
    spokesman_discount_translate = ''

    if is_discount:
        shop_discount_translate = translate(is_discount, discount_type, shop_discount, shop_full, shop_reduce)

        if 1 == discount_type:
            spokesman_discount_translate = translate(is_discount, discount_type, spokesman_discount, shop_full, shop_reduce)
        elif 2 == discount_type:
            spokesman_discount_translate = translate(is_discount, discount_type, shop_discount, shop_full, spokesman_discount)

    if 1 == discount_type:
        trade_price, activity_price = calculate_trade(discount, constant, is_activity, activity_type, activity_discount, activity_full, activity_reduce,
                                      is_discount, discount_type, spokesman_discount, shop_full, shop_reduce)
    elif 2 == discount_type:
        trade_price, activity_price = calculate_trade(discount, constant, is_activity, activity_type, activity_discount, activity_full, activity_reduce,
                                      is_discount, discount_type, shop_discount, shop_full, spokesman_discount)
    else:
        trade_price = total
        activity_price = discount

    activity_reduce = discount - activity_price
    discount_reduce, brokerage = calculate_brokerage(activity_price, is_discount, discount_type, shop_discount, shop_full, shop_reduce, spokesman_discount, is_brokerage)

    trade_price = fenceil(trade_price)
    discount_reduce = fenfloor(discount_reduce)
    brokerage = fenfloor(brokerage)

    return {'is_activity': is_activity, 'is_discount':is_discount, 'activity': activity_translate,
            'shop_discount': shop_discount_translate, 'spokesman_discount': spokesman_discount_translate, 'trade_price': trade_price,
            'activity_reduce': activity_reduce, 'discount_reduce': discount_reduce, 'brokerage': brokerage}

def calculate_trade_dict_discount(total, is_discount, discount_type, shop_discount, shop_full, shop_reduce, spokesman_discount, is_manager):
    return calculate_trade_dict(total, 0, False, None, None, None, None, is_discount, discount_type,
        shop_discount, shop_full, shop_reduce, spokesman_discount, is_manager)

def member_pay(pay_password, trade, price, wait=None):
    from common.models import Wallet, ShopMember, TradePay, TradeRecord
    from MyAbstract.exceptions import ValidationDict211Error
    from APNS import apns_push

    wallet = Wallet.objects.get(user=trade.buyer)

    if not wallet.check_password(pay_password):
        raise ValidationDict211Error('密码错误')

    try:
        member = ShopMember.objects.get(shop=trade.shop, user=trade.buyer)
    except ShopMember.DoesNotExist:
        raise ValidationDict211Error('不是会员')

    if member.loose_change < price:
        raise ValidationDict211Error('卡内余额不足')

    if not wait:
        member.loose_change -= price
        member.save(update_fields=['loose_change'])

    TradePay.objects.create(trade=trade, trade_price=price, charge_ratio=0, pay_type='member',
        pay_platform_expend=0, pay_success=not wait, pay_info='member',
        remain= member.loose_change if not wait else None, card_name=member.member_card.name)

    if 'discount' == trade.profile_type:
        profile = trade.tradediscountprofile
        profile.shop_earning = 0  # fenceil(price / profile.trade_price * profile.shop_earning)
        profile.owner_earning = 0  # fenceil(price / profile.trade_price * profile.shop_earning)
        profile.save(update_fields=['shop_earning', 'owner_earning'])

        record = TradeRecord.objects.create(trade=trade)
        apns_push.handle_trade_member_success(record)
    elif 'ticket' == trade.profile_type:
        trade.tickets.update(shop_earning=0, owner_earning=0)

    return member.loose_change