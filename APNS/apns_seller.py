import datetime, time
from packaging import version
from common.models import SellerNotifyMessage, TradeMessage, MyUser, Shop
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import timetuple
from .yunbaSDK import YunbaSeller
from SMS import SMS

def switch_ios_sound(user, ios_sound):
    default = "bingbong.aiff"

    apns_voice = user.myusersellersettingprofile.apns_voice
    platform = user.myusersellersettingprofile.platform
    ver = user.myusersellersettingprofile.version

    if not ios_sound:
        return default
    elif not apns_voice:
        return default
    elif 'Android' == platform:
        return default #for accident
    elif 'IOS' == platform:
        #if version.parse(ver) >= version.parse("10.0.0"):
        #    return None
        #else:
        #    return ios_sound
        return ios_sound
    else:
        return default

def pulish_alias(shop, title, msg, type, ios_sound=None):
    yunba = YunbaSeller()

    for item in shop.managers.all():
        ios_sound = switch_ios_sound(item, ios_sound)
        yunba.send_publish2_to_alias(item.username, title, msg, type, timetuple(), ios_sound)

def record_alias_notify(shop, event, msg):
    SellerNotifyMessage.objects.bulk_create([SellerNotifyMessage(event_id=event, shop=shop, user=item, message=msg) for item in shop.managers.all()])

def publish_alias_notify(shop, event, msg, type='notify', ios_sound=None):
    record_alias_notify(shop, event, msg)

    pulish_alias(shop, '通知消息', msg, type, ios_sound)

def publish_request_spokesman(shop):
    msg = "{0}有新的代言人申请".format(shop.name)
    publish_alias_notify(shop, 3, msg, 'notify_spoker_apply', 'notify_spoker_apply.mp3')

def pulish_cancel_spokesman(shop, nick):
    publish_alias_notify(shop, 1, "{0}取消了{1}的代言".format(nick, shop.name))

def record_alias_trade(shop, record, msg, status, event):
    for item in shop.managers.all():
        TradeMessage.objects.create(user=item, message=msg, record=record, status=status, event=event)

def publish_alias_trade(shop, record, msg, status, event, type='trade', ios_sound=None):
    record_alias_trade(shop, record, msg, status, event)

    return pulish_alias(shop, '交易消息', msg, type, ios_sound)

def handle_trade_success(record):
    trade = record.trade
    msg = "代理人{0}的好友{1}在{2}消费{3}元".format(trade.spokesman.nick_name, trade.buyer.nick_name, trade.shop.name, str(trade.trade_price))
    publish_alias_trade(trade.shop, record, msg, 3, 1, 'trade_pay', 'trade_pay.mp3')

def handle_trade_member_success(record):
    trade = record.trade
    msg = "会员{0}在{1}消费{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price))
    publish_alias_trade(trade.shop, record, msg, 3, 1, 'trade_member_pay', 'trade_member_pay.mp3')

def handle_trade_ticket_use(record):
    ticket = record.ticket
    trade = ticket.trade
    msg = "代理人{0}的好友{1}在{2}使用了套餐券消费{3}元"\
        .format(trade.spokesman.nick_name, trade.buyer.nick_name, trade.shop.name, ticket.trade_price)
    publish_alias_trade(trade.shop, record, msg, 3, 4, 'trade_combo', 'trade_combo.mp3')

def handle_trade_experience_use(record):
    ticket = record.ticket
    trade = ticket.trade
    msg = "{0}在{1}使用了体验券".format(trade.buyer.nick_name, trade.shop.name)
    publish_alias_trade(trade.shop, record, msg, 3, 4, 'trade_experience', 'trade_experience.mp3')

def handle_trade_member_create(record):
    from common.models import ShopMember
    trade = record.trade
    card_name = ShopMember.objects.get(shop=trade.shop, user=trade.buyer).member_card.name
    msg = "{0}在{1}充值了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price))
    publish_alias_trade(trade.shop, record, msg, 3, 6, 'trade_member_recharge', 'trade_member_recharge.mp3')
    publish_alias_notify(trade.shop, 5, "{0}成为{1}{2}".format(trade.buyer.nick_name, trade.shop.name, card_name))

def publish_trade_member_recharge(record):
    trade = record.trade
    msg = "{0}在{1}充值了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price))
    publish_alias_trade(trade.shop, record, msg, 3, 6, 'trade_member_recharge', 'trade_member_recharge.mp3')

def record_member_create(shop, nick, card_name):
    record_alias_notify(shop, 5, "为{0}在{1}办理{2}".format(nick, shop.name, card_name))

def record_member_recharge(record):
    trade = record.trade
    record_alias_trade(trade.shop, record, "{0}在{1}充值了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price)), 3, 6)

def record_member_consume(record):
    trade = record.trade
    record_alias_trade(trade.shop, record, "为{0}在{1}代扣{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price)), 3, 1)

def publish_cash(cash_record):
    publish_alias_notify(cash_record.shop, 6, '{0}于{1}结算{2}元至{3}尾号{4}中'
        .format(cash_record.shop.name, cash_record.request_time.date(), cash_record.cash,
                cash_record.request_bank_name, cash_record.request_acc_no[-4:]))
    
    SMS.SellerSMS().cash_sms(cash_record.shop.seller.phone_number, cash_record.shop.name, cash_record.request_time.date(),
                           cash_record.cash, cash_record.request_bank_name, cash_record.request_acc_no[-4:])
