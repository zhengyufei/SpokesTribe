from . import apns, apns_seller

def handle_trade_success(record):
    apns.handle_trade_success(record)
    apns_seller.handle_trade_success(record)

def handle_trade_member_success(record):
    apns.handle_trade_success(record)
    apns_seller.handle_trade_member_success(record)

def handle_trade_confirm(record):
    apns.handle_trade_confirm(record)

def handle_trade_ticket_use(record):
    apns.handle_trade_ticket_use(record)
    apns_seller.handle_trade_ticket_use(record)

def handle_trade_experience_use(record):
    apns.handle_trade_experience_use(record)
    apns_seller.handle_trade_experience_use(record)

def handle_trade_member_create(record):
    apns.handel_trade_member_create(record)
    apns_seller.handle_trade_member_create(record)

def handle_trade_member_recharge(record):
    apns.record_trade_member_recharge(record)
    apns_seller.publish_trade_member_recharge(record)

def handle_seller_member_create(user, shop, nick, card_name):
    apns.publish_member_create(user, nick, shop.name, card_name)
    apns_seller.record_member_create(shop, nick, card_name)

def handle_seller_member_recharge(record):
    apns.publish_member_recharge(record)
    apns_seller.record_member_recharge(record)

def handle_seller_member_consume(record):
    apns.publish_member_consume(record)
    apns_seller.record_member_consume(record)

def handle_seller_cash(cash_record):
    apns_seller.publish_cash(cash_record)

def handle_seller_cash(record):
    apns_seller.publish_cash(record)

