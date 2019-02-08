import datetime, time
from MyAbstract.exceptions import ValidationDict211Error
from common.models import NotifyMessage, TradeMessage, MyUser
from .yunbaSDK import YunbaBuyer

def pulish_alias(user, title, msg, type):
    yunba = YunbaBuyer()
    return yunba.send_publish2_to_alias(user.id, title, msg, type, int(time.mktime(datetime.datetime.now().timetuple())), "bingbong.aiff")

def pulish_alias_system(user, msg):
    #insert

    return pulish_alias(user, '系统消息', msg, 'system')

def record_alias_notify(user, event, msg):
    NotifyMessage.objects.create(event_id=event, user=user, message=msg)

def publish_alias_notify(user, event, msg):
    record_alias_notify(user, event, msg)

    return pulish_alias(user, '通知消息', msg, 'notify')

def record_request_spokesman(user, nick, shop_name):
    record_alias_notify(user, 3, "%s，您为%s申请代理资格，商家会在七个工作日内审核资格" % (nick, shop_name))

def publish_apply_spokesman(user, nick, shop_name):
    publish_alias_notify(user, 1, "%s，审核通过，恭喜你！成为%s的代理人" % (nick, shop_name))

def record_alias_trade(user, record, msg, status, event):
    TradeMessage.objects.create(user=user, message=msg, record=record, status=status, event=event)

def publish_alias_trade(user, record, msg, status, event):
    record_alias_trade(user, record, msg, status, event)
    return pulish_alias(user, '交易消息', msg, 'trade')

def handle_trade_success(record):
    trade = record.trade
    record_alias_trade(trade.buyer, record, "Hi！{0}，您在{1}消费了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price)), 1, 1)
    publish_alias_trade(trade.spokesman, record, "Hi！{0}，{1}在{2}消费了".format(trade.spokesman.nick_name, trade.buyer.nick_name, trade.shop.name), 2, 1)

def handle_trade_confirm(record):
    trade = record.trade
    publish_alias_trade(trade.spokesman, record, "{0}已返还佣金{1}元".format(trade.shop.name, trade.tradediscountprofile.brokerage), 2, 2)

def handle_trade_ticket_use(record):
    ticket = record.ticket
    trade = ticket.trade
    publish_alias_trade(trade.buyer, record, "Hi！{0}，您在{1}使用了套餐劵{2}元"
        .format(trade.buyer.nick_name, trade.shop.name, ticket.trade_price), 1, 4)
    publish_alias_trade(trade.spokesman, record, "Hi！{0}，{1}在{2}消费了，已返还佣金{3}元"
                        .format(trade.spokesman.nick_name, trade.buyer.nick_name, trade.shop.name, ticket.brokerage), 2, 4)
    publish_alias_trade(trade.spokesman, record, "代理人{0}的好友{1}在{2}使用了套餐券消费{3}元"
                        .format(trade.spokesman.nick_name, trade.buyer.nick_name, trade.shop.name, ticket.trade_price), 3, 4)

def handle_trade_experience_use(record):
    ticket = record.ticket
    trade = ticket.trade
    publish_alias_trade(trade.buyer, record, "Hi！{0}，您在{1}使用了体验券"
        .format(trade.buyer.nick_name, trade.shop.name), 1, 4)

def handel_trade_member_create(record):
    from common.models import ShopMember
    trade = record.trade
    card_name = ShopMember.objects.get(shop=trade.shop, user=trade.buyer).member_card.name
    record_alias_trade(trade.buyer, record, "Hi！{0}，您在{1}充值了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price)), 1, 6)
    record_alias_notify(trade.buyer, 5, "{0}，恭喜你成为{1}{2}".format(trade.buyer.nick_name, trade.shop.name, card_name))

def record_trade_member_recharge(record):
    trade = record.trade
    record_alias_trade(trade.buyer, record, "Hi！{0}，您在{1}充值了{2}元".format(trade.buyer.nick_name, trade.shop.name, str(trade.trade_price)), 1, 6)

def publish_member_create(user, nick, shop_name, card_name):
    publish_alias_notify(user, 5, "{0}，恭喜你成为{1}{2}".format(nick, shop_name, card_name))

def publish_member_recharge(record):
    user = record.trade.buyer
    publish_alias_trade(user=user, record=record, msg="Hi！{0}，商家在{1}为你办理了充值{2}元"
                         .format(user.nick_name, record.trade.shop.name, record.trade.trade_price), status=1, event=6)

def publish_member_consume(record):
    user = record.trade.buyer
    publish_alias_trade(user=user, record=record, msg="Hi！{0}，商家在{1}为你代扣了{2}元"
                         .format(user.nick_name, record.trade.shop.name, record.trade.trade_price), status=1, event=1)
