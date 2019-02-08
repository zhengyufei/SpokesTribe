#because Refund() used models, so it can't put in models.py, it will trigger error
def Trade_member(trade, pay):
    from .models import ShopMember, Trade
    from .refund import Refund
    member = ShopMember.objects.select_for_update().get(shop=trade.shop, user=trade.buyer)
    if member.loose_change < pay.trade_price:
        if trade.profile_type == 'discount':
            Refund().auto(trade.trade_number, 'member is lack')
        elif trade.profile_type == 'ticket':
            Refund().auto_ticket(trade.trade_number, trade.tickets.count(), 'member is lack')

        return False

    member.loose_change -= pay.trade_price
    member.save(update_fields=['loose_change'])
    pay.pay_success = True
    pay.save(update_fields=['pay_success'])

    return True