import datetime
import json

from dateutil.relativedelta import relativedelta
from django.db.models import F, Q
from django.utils import timezone

from Logger.logger import Logger
from Pay.Zhaoshang.ZhaoshangTransfer import PayForAnother
from common.function import is_festival
from common.models import ShopCombo, TradeDiscountProfile, TradeTicketProfile, TradeRecord, ShopWallet, ShopCashRecord, \
    TaxMonthRecord, Wallet, TradeMemberProfile, ShopFlyer, Flyer2Shop, Flyer2User
from common.refund import Refund
from myadmin.models import AutoShopCashRecord, CommandsRecord


def record(f):
    def wrapped_f(*args, **kwargs):
        user = kwargs['user'] if 'user' in kwargs.keys() else None
        name = kwargs['name'] if 'name' in kwargs.keys() else f.__name__

        record = CommandsRecord.objects.create(user=user, name=name)
        record = f(args[0], record) if len(args) > 0 else f(record) # T cls F func

        record.end_time = timezone.now()
        record.save(update_fields=['end_time', 'describe', 'remark'])
    return wrapped_f

@record
def combo_check(record):
    queryset2 = TradeTicketProfile.objects.filter(status='pay')
    queryset2.update(status='invalid')
    trades = {}
    for item in queryset2:
        if item.trade.id not in trades.keys():
            trades[item.trade.id] = []
        trades[item.trade.id].append(item.ticket_number)

    for key in trades:
        Refund().auto_ticket(key, trades[key], 'outtime')

    queryset = ShopCombo.objects.filter(status__in=('online', 'offline'), valid_period_end__lte=timezone.now())
    queryset.update(status='invalid', left_time=timezone.now())

    queryset = ShopFlyer.objects.filter(status__in=('online'), valid_period_end__lt=timezone.now())
    queryset.update(status='limit', left_time=timezone.now())
    Flyer2User.objects.filter(flyer__in=queryset, status='valid').update(status='invalid')

    record.status = 'success'
    return record

class ShopSettlement(object):
    def cash_check(self):
        if AutoShopCashRecord.objects.filter(result=True).exists():
            old_cash = AutoShopCashRecord.objects.filter(result=True).order_by('-id')[0]
            cash = AutoShopCashRecord.objects.create()
            if cash.exec_time < old_cash.exec_time + datetime.timedelta(hours=23):
                cash.result = False
                cash.save(update_fields=['result'])
        else:
            cash = AutoShopCashRecord.objects.create()

        return cash

    def brokerage(self, profile):
        profile.status = 'confirm'
        profile.confirm_time = timezone.now()
        profile.save(update_fields=['status', 'confirm_time'])

        trade = profile.trade

        try:
            record = TradeRecord.objects.get(trade=trade)
            record.confirm = True
            record.save(update_fields=['confirm'])
        except:
            pass

    def shop_confirm(self):
        # TODO
        queryset = TradeDiscountProfile.objects.filter(trade__has_pay=True, status='pay', trade__profile_type__in=('discount', ))
        for item in queryset:
            self.brokerage(item)

        queryset = TradeMemberProfile.objects.filter(trade__has_pay=True, status='pay', trade__profile_type__in=('member', ))
        for item in queryset:
            self.brokerage(item)

    def shop_cash_settle(self):
        queryset = ShopWallet.objects.filter(income__gt=F('min_income'))
        temp = []
        for item in queryset:
            try:
                ShopCashRecord.objects.create(shop_id=item.shop_id, loose_change=item.income, cash=item.income,
                    status='request', charge=0, request_bank_name=item.bankcard.bank.name,
                    request_acc_name=item.bankcard.name, request_acc_no=item.bankcard.card)
            except:
                temp.append(item.shop_id)

        if len(temp) > 0:
            queryset = queryset.exclude(shop_id__in=temp)

        queryset.update(income=0)

        temp.clear()
        queryset = ShopWallet.objects.filter(income2__gt=F('min_income2'))
        for item in queryset:
            try:
                ShopCashRecord.objects.create(shop_id=item.shop_id, loose_change=item.income2, cash=item.income2,
                    status='request', charge=0, request_bank_name=item.bankcard.bank.name,
                    request_acc_name=item.bankcard.name, request_acc_no=item.bankcard.card, temp_type=2)
            except:
                temp.append(item.shop_id)

        if len(temp) > 0:
            queryset = queryset.exclude(shop_id__in=temp)

        queryset.update(income2=0)

        ShopWallet.objects.filter(income_bank__gt=0).update(income_bank=0)

    def person_income1_settle(self):
        Wallet.objects.filter(income1__gt=0).update(income=F('income')+F('income1'))
        Wallet.objects.filter(income1__gt=0).update(income1=0)

    # TODO
    @classmethod
    @record
    def shop_settlement(cls, record):
        settle = ShopSettlement()

        cash = settle.cash_check()

        if False == cash.result:
            record.remark = 'too close'
            record.status = 'refuse'
            return record

        settle.shop_confirm()
        settle.shop_cash_settle()
        settle.person_income1_settle()

        cash.end_time = timezone.now()
        cash.result = True
        cash.save(update_fields=['end_time', 'result'])

        return record

def abstract_shop_cash(record, filter1, filter2):
    queryset = ShopCashRecord.objects.filter(filter1)

    for item in queryset:
        response = PayForAnother(item.number, item.request_bank_name, item.request_acc_no,
                                 item.request_acc_name, item.cash - item.charge)
        response = json.loads(str(response.post(), encoding="utf-8"))

        item.merch_time = timezone.now()
        item.bank_name = item.request_bank_name
        item.acc_no = item.request_acc_no
        item.acc_name = item.request_acc_name
        item.status = 'apply'
        item.handle_time = timezone.now()
        item.retcod = response['RETCOD']
        item.errmsg = response['ERRMSG']
        item.save(update_fields=['merch_time', 'bank_name', 'acc_no', 'acc_name',
                                 'status', 'handle_time', 'retcod', 'errmsg'])

    #####################################################################
    queryset = ShopCashRecord.objects.filter(filter2)

    for item in queryset:
        if item.request_time.weekday() in (4, 5, 6) and is_festival():
            continue

        response = PayForAnother(item.number, item.request_bank_name, item.request_acc_no,
                                 item.request_acc_name, item.cash - item.charge)
        response = json.loads(str(response.post(), encoding="utf-8"))

        item.merch_time = timezone.now()
        item.bank_name = item.request_bank_name
        item.acc_no = item.request_acc_no
        item.acc_name = item.request_acc_name
        item.status = 'apply'
        item.handle_time = timezone.now()
        item.retcod = response['RETCOD']
        item.errmsg = response['ERRMSG']
        item.save(update_fields=['merch_time', 'bank_name', 'acc_no', 'acc_name',
                                 'status', 'handle_time', 'retcod', 'errmsg'])

    record.status = 'success'
    return record

@record
def shop_cash(record):
    tmp = timezone.now() - datetime.timedelta(hours=59)
    filter1 = Q(status='request') & Q(request_time__lte=tmp) & Q(temp_type=1)
    tmp = timezone.now() - datetime.timedelta(hours=11)
    filter2 = Q(status='request') & Q(request_time__lte=tmp) & Q(temp_type=2)
    return abstract_shop_cash(record, filter1, filter2)

@record
def repair_shop_cash(record):
    filter1 = Q(status='request') & Q(temp_type=1)
    filter2 = Q(status='request') & Q(temp_type=2)
    return abstract_shop_cash(record, filter1, filter2)

@record
def tax(record):
    last = None

    try:
        last = CommandsRecord.objects.filter(name='tax', status='success').order_by('-id')[0]
    except:
        pass

    if last and (last.time + relativedelta(months=1)) > timezone.now():
        Logger.Log('info', 'error tax every month')
        record.status = 'refuse'
        return record

    queryset = Wallet.objects.all()

    for item in queryset:
        ex_remain, income, cash = item.remain, item.income, item.cash
        remain, tax = item.tax_month()
        item.save()
        TaxMonthRecord.objects.create(user=item.user, ex_remain=ex_remain, income=income, cash=cash, tax=tax,
                                      remain=remain)

    ShopWallet.objects.all().update(bonus_withdraw=0)

    record.status = 'success'
    return record
