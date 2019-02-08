import datetime
import decimal
import os
import uuid
from io import BytesIO
from PIL import Image
from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import F, Q

from MyAbstract.fields import *
from SpokesTribe.settings import APP_RATIO, SCAN_RATIO, FY_RATIO
from MyAbstract.funtions import RandomNumberString, services_contract
from .helpless import Trade_member
import common.settings as my_settings


def thumbnail(image):
    size = 128, 128
    file, ext = os.path.splitext(str(image))
    im = Image.open(image)
    im.thumbnail(size, Image.ANTIALIAS)

    imgOut = BytesIO()
    im.save(imgOut, 'JPEG', optimize=True, progressive=True)
    return SimpleUploadedFile(file + "_thumbnail.jpg", imgOut.getbuffer())

def create_trade_number():
    number = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    number += str(int(uuid.uuid1().hex, 16))[0:(32 - len(number))]

    return number

def create_ticket_number(len):
    number = str(int(uuid.uuid1().hex, 16))[0:len]

    return number

def create_refund_number():
    number = str(int(uuid.uuid1().hex, 16))[0:20]

    return number

# Create your models here.

class ShopFirstType(models.Model):
    name = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.name

class MyUser(AbstractUser):
    nick_name = models.CharField(max_length=32)
    female = models.NullBooleanField(null=True)
    birthday = models.DateField(null=True)
    phone_number = models.CharField(max_length=11, unique=True, null=True)
    abode = models.CharField(max_length=32, default='成都市')
    ico = models.ImageField(upload_to='user_ico')
    ico_thumbnail = models.ImageField(upload_to='user_ico')
    describe = models.TextField(blank=True, default='')

    def save(self, *args, **kwargs):
        if self.ico:
            self.ico_thumbnail = thumbnail(self.ico)

            if 'update_fields' in kwargs.keys():
                kwargs['update_fields'].append('ico_thumbnail')

        if not self.phone_number and len(self.username) <= 11:
            self.phone_number = self.username

            if 'update_fields' in kwargs.keys():
                kwargs['update_fields'].append('phone_number')

        super(MyUser, self).save(*args, **kwargs)

    def get_third(self):
        return self.third if hasattr(self, 'third') else MyUserThirdProfile.objects.create(user=self)

class MyUserSettingProfile(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True)

    no_disturb = models.BooleanField(default=False)
    no_disturb_seller = models.BooleanField(default=False)

class MyUserSellerSettingProfile(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True)

    no_disturb = models.BooleanField(default=False)
    apns_voice = models.BooleanField(default=True)

    PLATFORM = (
        ('Android', 'android'),
        ('IOS', 'ios'),
    )
    platform = models.CharField(choices=PLATFORM, null=True, max_length=8)
    version = models.CharField(null=True, max_length=32)

class MyUserThirdProfile(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True, related_name='third')

    weixin_unionid = models.CharField(max_length=64, null=True, unique=True)
    qq_unionid = models.CharField(max_length=64, null=True, unique=True)
    weibo_unionid = models.CharField(max_length=64, null=True, unique=True)
    zhifubao_unionid = models.CharField(max_length=64, null=True, unique=True)
    fy_wx_openid = models.CharField(max_length=64, null=True)
    fy_wx_oasis_openid = models.CharField(max_length=64, null=True)

class NationalId(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True)

    real_name = models.CharField(max_length=32)
    national_id = models.CharField(max_length=18, unique=True)
    national_id_front = models.ImageField(upload_to='national_id', null=True)
    national_id_back = models.ImageField(upload_to='national_id', null=True)
    is_valid = models.NullBooleanField(null=True, default=None)

class SmsVerCode(models.Model):
    phone = models.CharField(max_length=32)
    code = models.CharField(max_length=8)

    expire_time = models.DateTimeField()
    obsolete = models.NullBooleanField(null=True)
    resend_count = models.IntegerField(default=0)

class Shop(models.Model):
    seller = models.ForeignKey(MyUser, related_name='shop_sellser')
    managers = models.ManyToManyField(MyUser, through='ShopManagerShip', through_fields=('shop', 'user'))
    type = models.ForeignKey(ShopFirstType)

    STATE = (
        (1, '申请中'),
        (2, '审查失败'),
        (4, '运营'),
        (5, '冻结'),
        (6, '作废'),
    )
    state = models.IntegerField(choices=STATE, default=1)
    name = models.CharField(max_length=32, unique=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.CharField(max_length=256)
    phone = models.CharField(max_length=32, null=True)
    custom_type = models.CharField(max_length=8, blank=True, null=True)
    describe = models.TextField(default='')
    ico = models.ImageField(upload_to='shop_ico')
    ico_thumbnail = models.ImageField(upload_to='shop_ico')
    face = models.ImageField(null=True, upload_to='shop_face')
    level = models.DecimalField(max_digits=5, decimal_places=4, default=5)
    max_spoke = models.IntegerField(default=50)
    spoke_count = models.IntegerField(default=1)
    comment_count = models.IntegerField(default=0)
    open_time = models.TimeField()
    close_time = models.TimeField()
    city = models.CharField(max_length=32, db_index=True, default='成都市')
    join_time = models.DateTimeField(auto_now_add=True)
    staff_name = models.CharField(max_length=16, null=True)
    charge_ratio = models.IntegerField(default=40) #%% zs 30 other 40
    brokerage_ratio = models.IntegerField(default=20) #%
    league_count = models.IntegerField(default=0)

    BROKERAGE_TYPE = (
        (1, 'brokerage'),
        (2, 'bouns')
    )
    brokerage_type = models.IntegerField(choices=BROKERAGE_TYPE, default=1)
    combo_pay = models.BooleanField(default=False)

    convenience = models.TextField(blank=True, default='')
    announcement = models.TextField(blank=True, default='')

    PAY_TYPE = (
        (1, 'zhaoshang'),
        (2, 'fuyou'),
    )

    pay_type = models.IntegerField(choices=PAY_TYPE, default=2)

    def save(self, *args, **kwargs):
        if self.ico:
            self.ico_thumbnail = thumbnail(self.ico)

            if 'update_fields' in kwargs.keys():
                kwargs['update_fields'].append('ico_thumbnail')

        super(Shop, self).save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['seller']),
            models.Index(fields=['state']),
        ]

class ShopManagerShip(models.Model):
    shop = models.ForeignKey(Shop)
    user = models.ForeignKey(MyUser)

    name = models.CharField(max_length=32)
    join_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shop', 'user')

class ShopBusinessLicence(models.Model):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='business_licence')

    name = models.CharField(max_length=32)
    serial_number = models.CharField(max_length=32)
    valid_date = models.CharField(max_length=64)
    business_licence = models.ImageField(upload_to='shop_business_licence')

class ShopLicence(models.Model):
    shop = models.ForeignKey(Shop, related_name='licences')

    name = models.CharField(max_length=32)
    serial_number = models.CharField(max_length=32)
    valid_date = models.CharField(max_length=64)
    licence = models.ImageField(null=True, upload_to='shop_licence')

class ShopRequire(models.Model):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='require')

    require1 = models.TextField(default='正面积极的代理产品')
    require2 = models.TextField(default='创造和谐的代理环境')
    require3 = models.TextField(default='可以耐心为好友解决和讲解基本问题')

class ShopCombo(models.Model):
    shop = models.ForeignKey(Shop, related_name='combo')

    name = models.CharField(max_length=32)
    ico = models.ImageField(upload_to='shop_combo_ico')
    ico_thumbnail = models.ImageField(upload_to='shop_combo_ico')
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    activity_price = models.DecimalField(max_digits=10, decimal_places=2)
    join_time = models.DateTimeField(auto_now_add=True)
    left_time = models.DateTimeField(null=True)
    valid_period_begin = models.DateField(auto_now_add=True)
    valid_period_end = models.DateField()
    use_time = models.CharField(max_length=32)
    precautions = models.TextField(null=True, blank=True)
    tips = models.TextField(null=True, blank=True)
    festival = models.BooleanField(default=False)

    STATUS = (
        ('ready', '准备'),
        ('online', '上架'),
        ('offline', '下架'),
        ('invalid', '无效')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='ready')

    def save(self, *args, **kwargs):
        if self.ico:
            self.ico_thumbnail = thumbnail(self.ico)

            if 'update_fields' in kwargs.keys():
                kwargs['update_fields'].append('ico_thumbnail')

        super(ShopCombo, self).save(*args, **kwargs)

    def is_ready(self):
        return self.status == 'ready'

    def is_online(self):
        return self.status == 'online'

class AbstractShopComboGoods(models.Model):
    name = models.CharField(max_length=32)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    num = models.IntegerField()
    unit = models.CharField(max_length=4)

    class Meta:
        abstract = True

class ShopComboGoods(AbstractShopComboGoods):
    combo = models.ForeignKey(ShopCombo, related_name='goods')

class Bank(models.Model):
    name = models.CharField(max_length=16, unique=True)
    code = models.CharField(max_length=16, unique=True)
    image = models.ImageField(upload_to='bank', default='bank/default.jpg')

class AbstractBankCard(models.Model):
    bank = models.ForeignKey(Bank)
    type = models.CharField(max_length=32)
    card = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    phone = models.CharField(max_length=32)
    code = models.CharField(max_length=16, null=True)

    is_valid = models.BooleanField(default=True)

    class Meta:
        abstract = True

class Wallet(AbstractBaseUser):
    user = models.OneToOneField(MyUser, primary_key=True, related_name='wallet')

    remain = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_income = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    income1 = models.DecimalField(max_digits=10, decimal_places=2, default=0) #代付

    const_notax = 800

    # TODO
    @classmethod
    def income_pay(cls, id, income):
        Wallet.objects.filter(pk=id).update(income1=F('income1') + income)

    def max_cash(self):
        return self.remain + self.const_notax

    def cash_out(self):
        cash = self.remain_cash()
        self.cash += cash

        return cash

    def temp(self):
        return self.income + self.income1

    def loose_change(self):
        rtn = self.remain + self.temp() - self.cash

        return decimal.Decimal(rtn)

    def remain_cash(self):
        temp = self.temp()

        if temp > self.const_notax:
            rtn = self.remain + self.const_notax - self.cash
        else:
            rtn = temp - self.cash

        return decimal.Decimal(rtn)

    def no_cash(self):
        temp = self.temp()
        rtn = temp - self.const_notax if temp > self.const_notax else 0

        return decimal.Decimal(rtn)

    def tax_month(self):
        remain, tax = services_contract(self.income)
        self.remain += (remain - self.cash)
        self.income = 0
        self.cash = 0

        return self.remain, tax

class BankCard(AbstractBankCard):
    wallet = models.OneToOneField(Wallet, primary_key=True, related_name='bankcard')

class ShopWallet(AbstractBaseUser):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='wallet')
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_income = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    income2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_income2 = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    bonus_pool = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus_warning = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_bonus_free = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    bonus_withdraw = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    income_bank = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # only show

    @classmethod
    def income_pay(cls, id, income):
        ShopWallet.objects.filter(pk=id).update(income=F('income')+income)

    @classmethod
    def income_t1(cls, id, income):
        ShopWallet.objects.filter(pk=id).update(income2=F('income2')+income)

    @classmethod
    def income_collect(cls, id, income):
        ShopWallet.objects.filter(pk=id).update(income_bank=F('income_bank') + income)

    @classmethod
    def income_bonus(cls, id, income):
        ShopWallet.objects.filter(pk=id).update(bonus_pool=F('bonus_pool') + income)

    def loose_change(self):
        return self.income + self.income2 + self.income_bank

class ShopBankCard(AbstractBankCard):
    wallet = models.OneToOneField(ShopWallet, primary_key=True, related_name='bankcard')

class MyUserSpokeProfile(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True, related_name='spoke_profile')

    major_shop = models.ForeignKey(Shop, null=True)
    level = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    comment_count = models.IntegerField(default=0)

class AbstractDiscount(models.Model):
    is_valid = models.BooleanField(default=False)
    discount = IntegerRangeField(default=100, min_value=0, max_value=100)
    full_price = models.IntegerField(default=100)
    reduce_price = models.IntegerField(default=5)

    TYPE = (
        (1, 'discount'),
        (2, 'reduce')
    )
    type = models.IntegerField(choices=TYPE, default=1)

    class Meta:
        abstract = True

class ShopActivity(AbstractDiscount):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='activity')

    def __str__(self):
        if self.type == 1:
            return '商家活动%.1f折'%(self.discount/10.0)
        elif self.type == 2:
            return '商家活动满%d减%d'%(self.full_price, self.reduce_price)

        return ""

class ShopDiscount(AbstractDiscount):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='discount')

    def __str__(self):
        if self.type == 1:
            return '%0.1f折'%(self.discount/10.0)
        elif self.type == 2:
            return '满%d减%d'%(self.full_price, self.reduce_price)

        return ""

class ShopPhoto(models.Model):
    shop = models.ForeignKey(Shop, related_name='photos')

    photo = models.ImageField(upload_to='shop_photo')
    photo_thumbnail = models.ImageField(upload_to='shop_photo')

    def save(self, *args, **kwargs):
        if self.photo:
            self.photo_thumbnail = thumbnail(self.photo)

        super(ShopPhoto, self).save(*args, **kwargs)

class SpokesmanResume(models.Model):
    user = models.OneToOneField(MyUser, primary_key=True, related_name='resume')

    work = models.CharField(max_length=32, null=True, blank=True)
    resume = models.TextField(default='', null=True, blank=True)

class ShopSpokeRequest(models.Model):
    shop = models.ForeignKey(Shop)
    resume = models.ForeignKey(SpokesmanResume, related_name='request')

    request = models.TextField()
    request_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shop', 'resume')

class ShopSpokeRequestHistory(models.Model):
    shop = models.ForeignKey(Shop)
    spokesman = models.ForeignKey(MyUser)

    request_time = models.DateTimeField()
    handle_time = models.DateTimeField(auto_now_add=True)
    result = models.BooleanField()

class ShopPayZSProfile(models.Model):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='zhaoshang')

    open_id = models.CharField(max_length=32, null=True, unique=True)
    open_key = models.CharField(max_length=32, null=True, unique=True)
    password = models.CharField(max_length=6, default='123456')

    TYPE = (
        ('person', 'person'),
        ('shop', 'shop')
    )
    type = models.CharField(choices=TYPE, max_length=8, default='shop')

class ShopPayFYProfile(models.Model):
    shop = models.OneToOneField(Shop, primary_key=True, related_name='fuyou', on_delete=models.DO_NOTHING)
    merchant_no = models.CharField(max_length=16)
    terminal_id = models.CharField(max_length=8)
    access_token = models.CharField(max_length=32)
    is_wx_oasis = models.BooleanField(default=False)

class ShopFlyer(models.Model):
    shop = models.ForeignKey(Shop)

    img = models.ImageField(upload_to='spoker_shop_img')
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    join_time = models.DateTimeField(auto_now_add=True)
    left_time = models.DateTimeField(null=True)
    valid_period_begin = models.DateField(auto_now_add=True)
    valid_period_end = models.DateField()
    day_begin = models.TimeField()
    day_end = models.TimeField()
    festival = models.BooleanField(default=False)
    precautions = models.TextField(null=True, blank=True)
    tips = models.TextField(null=True, blank=True)

    TYPE = (
        (1, '折扣券'),
        (2, '抵用券'),
        (3, '体验券')
    )
    type = models.IntegerField(choices=TYPE)

    STATUS = (
        ('online', '上架'),
        ('offline', '下架'),
        ('invalid', '无效'),
        ('limit', '受限')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='online')

class ShopFlyerDiscountProfile(models.Model):
    flyer = models.OneToOneField(ShopFlyer, primary_key=True, related_name='discount')

    discount = models.IntegerField(default=100)
    full_price = models.IntegerField(default=100)

    BONUS_TYPE = (
        (1, '固定金额'),
        (2, '固定比例')
    )
    bonus_type = models.IntegerField(choices=BONUS_TYPE)

class ShopFlyerReduceProfile(models.Model):
    flyer = models.OneToOneField(ShopFlyer, primary_key=True, related_name='reduce')

    full_price = models.IntegerField(default=100)
    reduce_price = models.IntegerField(default=0)

class ShopFlyerExperienceProfile(models.Model):
    flyer = models.OneToOneField(ShopFlyer, primary_key=True, related_name='experience')

    name = models.CharField(max_length=16)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)

class ShopFlyerExperienceGoods(AbstractShopComboGoods):
    combo = models.ForeignKey(ShopFlyerExperienceProfile, related_name='goods')

class Flyer2Shop(models.Model):
    shop = models.ForeignKey(Shop)
    flyer = models.ForeignKey(ShopFlyer)

    count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('shop', 'flyer')

class Flyer2UserManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs['ticket_number'] = create_ticket_number(14)

        return super(Flyer2UserManager, self).create(*args, **kwargs)

class Flyer2User(models.Model):
    objects = Flyer2UserManager()

    user = models.ForeignKey(MyUser)
    shop = models.ForeignKey(Shop)
    flyer = models.ForeignKey(ShopFlyer)

    ticket_number = models.CharField(max_length=14, unique=True)
    time = models.DateTimeField(auto_now_add=True)

    STATUS = (
        ('valid', '有效'),
        ('used', '已使用'),
        ('settled', '已结算'),
        ('invalid', '无效'),
    )
    status = models.CharField(choices=STATUS, max_length=8, default='valid')
    bonus = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    trade = models.ForeignKey('Trade', null=True, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = ('user', 'flyer')

class TradeManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs['trade_number'] = create_trade_number()
        shop = kwargs['shop'] if 'shop' in kwargs.keys() else Shop.objects.get(id=kwargs['shop_id'])
        kwargs['charge_ratio'] = shop.charge_ratio
        kwargs['brokerage_ratio'] = shop.brokerage_ratio

        return super(TradeManager, self).create(*args, **kwargs)

class Trade(models.Model):
    objects = TradeManager()

    shop = models.ForeignKey(Shop)
    buyer = models.ForeignKey(MyUser)
    spokesman = models.ForeignKey(MyUser, related_name='spoker')

    shop_discount = models.CharField(max_length=16, null=True)
    discount = models.CharField(max_length=16, null=True)
    total_fee = models.DecimalField(max_digits=8, decimal_places=2)
    trade_price = models.DecimalField(max_digits=8, decimal_places=2)
    trade_time = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    trade_number = models.CharField(max_length=32, unique=True)
    has_pay = models.BooleanField(default=False)
    charge_ratio = models.IntegerField()  # %%
    brokerage_ratio = models.IntegerField()  # %

    PROFILE_TYPE = (
        ('discount', 'discount'),
        ('ticket', 'ticket'),
        ('member', 'member'),
        ('experien', 'experience'),
    )
    profile_type = models.CharField(choices=PROFILE_TYPE, max_length=8)

    SETTLE_TYPE = (
        ('pay', 'pay'), #代付
        ('collect', 'collect'), #代扣
        ('nothing', 'nothing') #不用结算
    )
    settle_type = models.CharField(choices=SETTLE_TYPE, max_length=8, null=True)

    def set_settle_type(self):
        pay_type_set = self.pay_type()

        for item in pay_type_set:
            if item in ['zb_wx', 'zb_ali'] \
                and self.shop.zhaoshang.type == 'shop' \
                and self.profile_type in ['discount', 'member']:
                self.settle_type = 'collect'
                break

            if item not in ['member', 'offline']:
                self.settle_type = 'pay'
                break
        else:
            self.settle_type = 'nothing'

        self.save(update_fields=['settle_type'])

    def pay_back(self, success, info, fy_trade_no=None):
        rtn = True

        for item in self.tradepay_set.all():
            if 'member' == item.pay_type:
                temp = Trade_member(self, item)
                if rtn and not temp:
                    rtn = temp #rtn is False now

                break

        for item in self.tradepay_set.all():
            if 'member' != item.pay_type:
                plat_ratio = item.pay_back(success, info, fy_trade_no)
                self.brokerage(plat_ratio)

                break

        return rtn

    def brokerage(self, plat_ratio):
        charge_ratio = decimal.Decimal(self.shop.charge_ratio / 10000)
        brokerage_ratio = decimal.Decimal(self.shop.brokerage_ratio / 100)

        if self.profile_type == 'discount':
            self.tradediscountprofile.brokerage_func(plat_ratio, charge_ratio, brokerage_ratio)
        elif self.profile_type == 'ticket':
            for item in self.tickets.all():
                item.brokerage_func(plat_ratio, charge_ratio, brokerage_ratio)

    def pay_type(self, display=False):
        rtn = []
        for item in self.tradepay_set.all():
            rtn.append(item.get_pay_type_display()) if display else rtn.append(item.pay_type)

        return rtn

    def __str__(self):
        return self.trade_number

class TradePay(models.Model):
    trade = models.ForeignKey(Trade)
    trade_price = models.DecimalField(max_digits=8, decimal_places=2)
    charge_ratio = models.IntegerField()
    pay_type = models.CharField(choices=my_settings.PAY_TYPE, max_length=8, null=True)
    pay_platform_expend = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    pay_success = models.BooleanField(default=False)
    pay_info = models.TextField(null=True)
    zhaobank_no = models.CharField(max_length=64, null=True, unique=True)
    is_seller = models.BooleanField(default=False)
    remain = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    card_name = models.CharField(null=True, max_length=16)
    fuyou_trade_no = models.CharField(max_length=64, null=True, unique=True)

    class Meta:
        unique_together = ('trade', 'pay_type')

    def pay_back(self, success, info, fy_trade_no=None):
        if not success:
            return

        self.trade.has_pay = True
        self.trade.save(update_fields=['has_pay'])
        update_fields = []
        if self.pay_type in ('weixin', 'ali'):
            plat_ratio = APP_RATIO
        elif self.pay_type in ('zb_wx', 'zb_ali'):
            plat_ratio = SCAN_RATIO
        elif self.pay_type in ('fy_wxjs', 'fy_alijs'):
            self.fuyou_trade_no = fy_trade_no
            update_fields.append('fuyou_trade_no')
            plat_ratio = FY_RATIO
        else:
            plat_ratio = 0

        self.pay_success = success
        self.pay_info = info
        self.pay_platform_expend = self.trade_price * plat_ratio
        update_fields.extend(['pay_success', 'pay_info', 'pay_platform_expend'])
        self.save(update_fields=update_fields)

        return plat_ratio

class TradeRefundManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs['refund_number'] = create_refund_number()
        kwargs['status'] = 'refund' if kwargs['auto'] else 'request'

        return super(TradeRefundManager, self).create(*args, **kwargs)

class TradeRefund(models.Model):
    objects = TradeRefundManager()

    trade = models.ForeignKey(Trade)

    request_time = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    refund_number = models.CharField(max_length=20)
    auto = models.BooleanField()
    operator = models.CharField(max_length=16)

    REASON = (
        ('refuse', '商家拒绝接待'),
        ('difference', '商品与描述不相符'),
        ('error_order', '订单下错了'),
        ('repetition', '重复下单'),
        ('other', '其他')
    )
    reason = models.CharField(choices=REASON, null=True, max_length=16)
    online_success = models.BooleanField(default=False)
    online_info = models.TextField(null=True)
    refund_time = models.DateTimeField(auto_now_add=True)

    STATUS = (
        ('request', '退款申请'),
        ('refund', '退款中'),
        ('success', '退款成功'),
        ('fail', '退款失败'),
    )
    status = models.CharField(choices=STATUS, null=True, max_length=8)
    member_remain = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        unique_together = ('trade', 'refund_number')

class AbstractTradeProfile(models.Model):
    trade_price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_reduce = models.DecimalField(max_digits=8, decimal_places=2)
    brokerage_design = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    brokerage = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    shop_earning = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    pay_platform_expend = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    owner_earning = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    owner_brokerage = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    confirm_time = models.DateTimeField(null=True)

    STATUS = (
        ('init', 'init'),
        ('pay', '支付 或 未使用'),
        ('torefund', '退款中'),
        ('refund', '已退款'),
        ('refund_fail', '退款失败'),
        ('invalid', '无效'),
        ('confirm', '确认 或 使用'),
        ('tosettle', '结算中'),
        ('settle', '已结算'),
        ('settle_fail', '结算失败'),
    )
    status = models.CharField(choices=STATUS, max_length=16, default='init')

    def set_status(self, status, save=False):
        if ('init' == self.status and status in ['pay', ])\
            or ('pay' == self.status and status in ['torefund', 'confirm'])\
            or ('torefund' == self.status and status in ['refund', 'refund_fail'])\
            or ('refund_fail' == self.status and status in ['refund', ])\
            or ('confirm' == self.status and status in ['tosettle']) \
            or ('tosettle' == self.status and status in ['settle', 'settle_fail']) \
            or ('settle_fail' == self.status and status in ['settle', ]):
            self.status = status

            if save:
                self.save(update_fields=['status'])
        #else:
        #    raise ValueError('error')

        return self.status

    class Meta:
        abstract = True

class TradeDiscountProfile(AbstractTradeProfile):
    trade = models.OneToOneField(Trade, primary_key=True)
    refund = models.OneToOneField(TradeRefund, null=True)
    ticket = models.ForeignKey(Flyer2User, null=True)

    activity = models.CharField(max_length=16, null=True)
    activity_reduce = models.DecimalField(max_digits=8, decimal_places=2)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2)
    constant_price = models.DecimalField(max_digits=8, decimal_places=2)

    def brokerage_func(self, plat_ratio, charge_ratio, brokerage_ratio):
        if 2 == self.trade.shop.brokerage_type:
            wallet = ShopWallet.objects.select_for_update().get(shop=self.trade.shop)
            if wallet.bonus_pool >= self.brokerage_design:
                brokerage_amount = self.brokerage_design
                wallet.bonus_pool -= self.brokerage_design
            else:
                brokerage_amount = wallet.bonus_pool
                wallet.bonus_pool = 0

            wallet.save(update_fields=['bonus_pool'])
        else:
            brokerage_amount = self.brokerage_design
        brokerage = brokerage_amount * (1 - brokerage_ratio)
        self.set_status('pay')
        self.brokerage = brokerage
        self.owner_brokerage = brokerage_amount - brokerage
        self.shop_earning = self.trade.trade_price * (1 - charge_ratio) - brokerage_amount
        self.pay_platform_expend = self.trade_price * plat_ratio
        self.owner_earning = self.trade_price * (charge_ratio - plat_ratio)
        self.save(update_fields=['status', 'brokerage', 'owner_brokerage',
             'shop_earning', 'pay_platform_expend', 'owner_earning'])

class TradeTicketProfileManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs['ticket_number'] = create_ticket_number(12)

        return super(TradeTicketProfileManager, self).create(*args, **kwargs)

class TradeTicketProfile(AbstractTradeProfile):
    objects = TradeTicketProfileManager()

    #shop is necessary for judge ticket number
    trade = models.ForeignKey(Trade, related_name='tickets')
    shop = models.ForeignKey(Shop)
    combo = models.ForeignKey(ShopCombo)
    refund = models.ForeignKey(TradeRefund, related_name='tickets', null=True)

    ticket_number = models.CharField(max_length=12, unique=True)

    class Meta:
        unique_together = ('shop', 'ticket_number')

    def __str__(self):
        return self.ticket_number

    def brokerage_func(self, plat_ratio, charge_ratio, brokerage_ratio):
        if 1 == self.trade.shop.brokerage_type:
            brokerage_amount = self.brokerage_design
            brokerage = brokerage_amount * (1 - brokerage_ratio)
            self.set_status('pay')
            self.brokerage = brokerage
            self.owner_brokerage = brokerage_amount - brokerage
            self.shop_earning = self.trade.trade_price * (1 - charge_ratio) - brokerage_amount
            self.pay_platform_expend = self.trade_price * plat_ratio
            self.owner_earning = self.trade_price * (charge_ratio - plat_ratio)
            self.save(update_fields=['status', 'brokerage', 'owner_brokerage',
                'shop_earning', 'pay_platform_expend', 'owner_earning'])
        elif 2 == self.trade.shop.brokerage_type:
            self.set_status('pay')
            self.pay_platform_expend = self.trade_price * plat_ratio
            self.owner_earning = self.trade_price * (charge_ratio - plat_ratio)
            self.save(update_fields=['status', 'pay_platform_expend', 'owner_earning'])

    #this is type 2
    def confirm(self, charge_ratio, brokerage_ratio):
        if 2 != self.trade.shop.brokerage_type:
            return

        wallet = ShopWallet.objects.select_for_update().get(shop=self.trade.shop)
        if wallet.bonus_pool >= self.brokerage_design:
            brokerage_amount = self.brokerage_design
            wallet.bonus_pool -= self.brokerage_design
        else:
            brokerage_amount = wallet.bonus_pool
            wallet.bonus_pool = 0

        wallet.save(update_fields=['bonus_pool'])

        brokerage = brokerage_amount * (1 - brokerage_ratio)

        self.status = 'confirm'
        self.confirm_time = datetime.datetime.now()
        self.brokerage = brokerage
        self.owner_brokerage = brokerage_amount - brokerage
        self.shop_earning = self.trade.trade_price * (1 - charge_ratio) - brokerage_amount
        self.save(update_fields=['status', 'confirm_time', 'brokerage', 'owner_brokerage', 'shop_earning'])

class TradeExperienceProfile(AbstractTradeProfile):
    trade = models.OneToOneField(Trade, primary_key=True)
    ticket = models.ForeignKey(Flyer2User)

class TradeRecord(models.Model):
    trade = models.OneToOneField(Trade, null=True)
    ticket = models.OneToOneField(TradeTicketProfile, null=True)
    experience = models.OneToOneField(TradeExperienceProfile, null=True)

    time = models.DateTimeField(auto_now_add=True)
    confirm = models.BooleanField(default=False)

class TradeShop(models.Model):
    shop = models.ForeignKey(Shop)

    trade_price = models.DecimalField(max_digits=8, decimal_places=2)
    trade_time = models.DateTimeField(auto_now_add=True)
    trade_number = models.CharField(max_length=32, unique=True)
    has_pay = models.BooleanField(default=False)

    def pay_back(self, success, info):
        if not self.has_pay:
            self.has_pay = True
            self.save(update_fields=['has_pay'])

            self.pay.pay_back(success, info)

            return True

        return False

class TradeShopPay(models.Model):
    trade = models.OneToOneField(TradeShop, primary_key=True, related_name='pay')

    PAY_TYPE = (
        ('weixin', '微信'),
        ('ali', '支付宝'),
        ('zb_wx', '微信'),
        ('zb_ali', '支付宝')
    )
    pay_type = models.CharField(choices=PAY_TYPE, max_length=8, null=True)
    pay_platform_expend = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    pay_success = models.BooleanField(default=False)
    pay_info = models.TextField(null=True)
    zhaobank_no = models.CharField(max_length=64, null=True, unique=True)

    class Meta:
        unique_together = ('trade', 'pay_type')

    def pay_back(self, success, info):
        if not success:
            return False

        self.pay_success = success
        self.pay_info = info

        if self.pay_type == 'weixin' or self.pay_type == 'ali':
            plat_ratio = APP_RATIO
        elif self.pay_type == 'zb_wx' or self.pay_type == 'zb_ali':
            plat_ratio = SCAN_RATIO
        else:
            plat_ratio = 0

        self.pay_platform_expend = self.trade.trade_price * plat_ratio

        self.save(update_fields=['pay_success', 'pay_info', 'pay_platform_expend'])

        return True

class Comment(models.Model):
    trade = models.OneToOneField(Trade, primary_key=True)

    comment = models.TextField()
    time = models.DateTimeField(auto_now_add=True)

class CommentPhoto(models.Model):
    comment = models.ForeignKey(Comment, related_name='photos')
    photo = models.ImageField(null=True, upload_to='comment')
    photo_thumbnail = models.ImageField(null=True, upload_to='comment')

    def __str__(self):
        return self.photo

    def save(self, *args, **kwargs):
        if self.photo:
            self.photo_thumbnail = thumbnail(self.photo)

        super(CommentPhoto, self).save(*args, **kwargs)

class CollectShop(models.Model):
    user = models.ForeignKey(MyUser)
    shop = models.ForeignKey(Shop)

    class Meta:
        unique_together = ('user', 'shop')

class FriendGroup(models.Model):
    user = models.ForeignKey(MyUser)

    name = models.CharField(max_length=32)

    TYPE = (
        (1, 'turkey not into shop_spoke_groups'),
        (2, 'brother, not into shop_spoke_group'),
        (3, 'friend'),
    )
    type = models.IntegerField(choices=TYPE)

    class Meta:
        unique_together = ('user', 'type')

class Friend(models.Model):
    user = models.ForeignKey(MyUser, related_name='friend_user')
    friend = models.ForeignKey(MyUser, related_name='friend_friend')
    group = models.ForeignKey(FriendGroup)

    alias = models.CharField(max_length=32, null=True)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend')

class Feedback(models.Model):
    user = models.ForeignKey(MyUser)

    feedback = models.TextField()
    contact = models.CharField(max_length=32, null=True)
    time = models.DateTimeField(auto_now_add=True)

class AbstractMessage(models.Model):
    message = models.CharField(max_length=64)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class SystemMessage(AbstractMessage):
    user = models.ForeignKey(MyUser)

#class SellerSystemMessage(AbstractMessage):
#    user = models.ForeignKey(MyUser)

class NotifyEvent(models.Model):
    event = models.CharField(max_length=32)

    def __str__(self):
        return self.event

class NotifyMessage(AbstractMessage):
    user = models.ForeignKey(MyUser)
    event = models.ForeignKey(NotifyEvent)

class SellerNotifyMessage(AbstractMessage):
    user = models.ForeignKey(MyUser)
    shop = models.ForeignKey(Shop)
    event = models.ForeignKey(NotifyEvent)

class TradeMessage(AbstractMessage):
    user = models.ForeignKey(MyUser)
    record = models.ForeignKey(TradeRecord)

    STATUS = (
        (1, 'buyer'),
        (2, 'agent'),
        (3, 'shop'),
    )
    status = models.IntegerField(choices=STATUS)

    EVENT = (
        (1, 'trade discount buy'),
        (2, 'trade discount confirm'),
        (3, 'trade ticket buy'),
        (4, 'trade ticket use'),
        (5, 'trade ticket refund'),
        (6, 'member charge')
    )
    event = models.IntegerField(choices=EVENT)

class AbstractCash(models.Model):
    loose_change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    request_time = models.DateTimeField(auto_now_add=True)
    handle_time = models.DateTimeField(null=True)

    STATUS = (
        ('request', '申请中'),
        ('wait', '等待审核'),
        ('apply', '银行处理中'),
        ('success', '成功'),
        ('fail', '失败'),
        ('waitback', '失败等待处理'),
        ('return', '失败转回钱包'),
    )
    status = models.CharField(choices=STATUS, default='request', max_length=8)
    remark = models.TextField()
    number = models.CharField(max_length=30, unique=True)
    charge = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    request_bank_name = models.CharField(max_length=20)
    request_acc_no = models.CharField(max_length=35)
    request_acc_name = models.CharField(max_length=60)
    merch_time = models.DateTimeField(null=True) #as doc
    bank_name = models.CharField(max_length=20) #as doc
    acc_no = models.CharField(max_length=35) #as doc
    acc_name = models.CharField(max_length=60) #as doc
    retcod = models.CharField(max_length=4, null=True) #response
    errmsg = models.CharField(max_length=128, null=True) #response
    bank_time = models.DateTimeField(null=True) #as doc
    bank_code = models.CharField(max_length=7, null=True) #as doc
    bank_msg = models.CharField(max_length=80) #as doc

    def create_cash_number(self):
        number = self.head
        number += datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        number += str(int(uuid.uuid1().hex, 16))[0:(30 - len(number))]

        return number

    def save(self, *args, **kwargs):
        self.number = self.create_cash_number()

        super(AbstractCash, self).save(*args, **kwargs)

    class Meta:
        abstract = True

class CashRecord(AbstractCash):
    user = models.ForeignKey(MyUser)

    head = 'PERSON'

    def save(self, *args, **kwargs):
        self.number = self.create_cash_number()

        super(CashRecord, self).save(*args, **kwargs)

class ShopCashRecord(AbstractCash):
    shop = models.ForeignKey(Shop)

    head = 'SHOP'
    TEMP_TYPE = (
        (1, 'T+3'),
        (2, 'T+1'),
    )
    temp_type = models.IntegerField(choices=TEMP_TYPE, default=1)

class ShopWithdrawRecord(AbstractCash):
    shop = models.ForeignKey(Shop)

    head = 'SW'

class RandomNickImage(models.Model):
    nick = models.CharField(max_length=8, unique=True)
    image = models.ImageField(upload_to='random_nick_image', default='random_nick_image/default.jpg')

class AdminOperateRecord(models.Model):
    user = models.ForeignKey(MyUser)

    time = models.DateTimeField(auto_now_add=True)

    TYPE = (
        ('tax', ''),
    )
    type = models.CharField(choices=TYPE, max_length=8)

    STATUS = (
        ('success', 'SUCCESS'),
        ('fail', 'FAIL'),
        ('refuse', 'REFUSE'),
    )
    status = models.CharField(choices=STATUS, max_length=8)

class TaxMonthRecord(models.Model):
    user = models.ForeignKey(MyUser)

    time = models.DateTimeField(auto_now_add=True)
    ex_remain = models.DecimalField(max_digits=10, decimal_places=2)
    income = models.DecimalField(max_digits=10, decimal_places=2)
    cash = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    remain = models.DecimalField(max_digits=10, decimal_places=2)

class Version(models.Model):
    version = models.CharField(max_length=32)
    min_version = models.CharField(max_length=32)
    time = models.DateTimeField(auto_now_add=True)

    TYPE = (
        ('Android', 'android'),
        ('IOS', 'ios'),
    )
    type = models.CharField(choices=TYPE, max_length=8)

    def __str__(self):
        return self.version

class CurrentVersion(models.Model):
    version = models.OneToOneField(Version, primary_key=True)

    TYPE = (
        ('Android', 'android'),
        ('IOS', 'ios'),
    )
    type = models.CharField(choices=TYPE, max_length=8)

    def __str__(self):
        return self.version.version

class Party(models.Model):
    organizer = models.ForeignKey(MyUser)

    name = models.CharField(max_length=32)
    describe = models.TextField(blank=True, default='')
    organizer_time = models.DateTimeField(auto_now_add=True)
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=64)
    location_detail = models.CharField(max_length=64, null=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    image = models.ImageField(upload_to='party')
    image_thumbnail = models.ImageField(upload_to='party')
    max_persons = models.IntegerField(null=True)

    STATUS = (
        ('valid', '有效'),
        ('over', '已结束'),
        ('cancel', '已取消'),
        ('invalid', '无效')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='valid')

    def save(self, *args, **kwargs):
        if self.image:
            self.image_thumbnail = thumbnail(self.image)

            if 'update_fields' in kwargs.keys():
                kwargs['update_fields'].append('image_thumbnail')

        super(Party, self).save(*args, **kwargs)

class PartyPerson(models.Model):
    party = models.ForeignKey(Party, related_name='persons')
    user = models.ForeignKey(MyUser)

    join_time = models.DateTimeField(auto_now_add=True)
    person_count = models.IntegerField(default=1)
    remark = models.CharField(null=True, max_length=64, default='精彩活动不容错过，大家快来参与吧！')

    class Meta:
        unique_together = ('party', 'user')

class PartyMessageBoard(models.Model):
    party = models.ForeignKey(Party, related_name='message_board')
    user = models.ForeignKey(MyUser)

    time = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    reply_id = models.IntegerField(null=True) #ForeignKey(PartyMessageBoard)

class ShopMemberCard(models.Model):
    shop = models.ForeignKey(Shop)

    name = models.CharField(max_length=32)
    image = models.ImageField(upload_to='shop_member_card')
    level = models.IntegerField(default=0)
    describe = models.TextField(default='')
    STATUS = (
        ('valid', '有效'),
        ('invalid', '无效')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='valid')

    class Meta:
        unique_together = ('shop', 'name')

class CardDiscount(models.Model):
    member_card = models.OneToOneField(ShopMemberCard, primary_key=True, related_name='discount')

    type = models.IntegerField(default=1)
    discount = models.IntegerField(default=100)
    full_price = models.IntegerField(default=100)
    reduce_price = models.IntegerField(default=5)

class AbstractShopMember(models.Model):
    user = models.ForeignKey(MyUser)
    shop = models.ForeignKey(Shop)
    member_card = models.ForeignKey(ShopMemberCard)

    name = models.CharField(max_length=32)
    phone = models.CharField(max_length=11)
    loose_change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remark = models.CharField(null=True, blank=True, max_length=64)

    class Meta:
        abstract = True

class ShopMember(AbstractShopMember):
    member_card = models.ForeignKey(ShopMemberCard, related_name='member')

    class Meta:
        unique_together = ('shop', 'user')

class ShopSpoke(models.Model):
    shop = models.ForeignKey(Shop)
    spokesman = models.ForeignKey(MyUser, null=True)
    member = models.ForeignKey(ShopMember, null=True)

    begin_time = models.DateTimeField(auto_now_add=True)

    TYPE = (
        ('normal', 'normal'),
        ('member', 'member'),
        ('master', 'master'),
    )
    type = models.CharField(choices=TYPE, max_length=8)

    class Meta:
        unique_together = ('shop', 'spokesman', 'member')

class ShopSpokeGroup(models.Model):
    shop = models.ForeignKey(Shop)
    group = models.ForeignKey(FriendGroup)
    #when shop discount type 1, discount > shop'discount
    #when shop discount type 2, discount < reduce_price
    discount = models.IntegerField(default=100)
    member_discount = models.IntegerField(default=100)

    class Meta:
        unique_together = ('shop', 'group')

class ShopMemberDelSnap(AbstractShopMember):
    old_id = models.IntegerField()

    @classmethod
    def set(cls, member):
        ectype = {k: v for k, v in member.__dict__.items() if not k.startswith('_')}
        ectype['old_id'] = ectype['id']
        del ectype['id']

        return ectype

class ShopMemberService(models.Model):
    shop = models.ForeignKey(Shop)

    name = models.CharField(max_length=32)

    STATUS = (
        ('valid', '有效'),
        ('invalid', '无效')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='valid')

    class Meta:
        unique_together = ('shop', 'name')

class ShopMemberTimeProfile(models.Model):
    member = models.ForeignKey(ShopMember, related_name='time_set')
    service = models.ForeignKey(ShopMemberService)

    expire_time = models.DateTimeField()

    class Meta:
        unique_together = ('member', 'service')

class ShopMemberCountProfile(models.Model):
    member = models.ForeignKey(ShopMember, related_name='count_set')
    service = models.ForeignKey(ShopMemberService)

    count = models.IntegerField()

    class Meta:
        unique_together = ('member', 'service')

class AbstractShopMemberRecharge(models.Model):
    shop = models.ForeignKey(Shop)
    member_card = models.ForeignKey(ShopMemberCard)

    name = models.CharField(max_length=16, default='')
    recharge = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    STATUS = (
        ('valid', '有效'),
        ('invalid', '无效')
    )
    status = models.CharField(choices=STATUS, max_length=8, default='valid')

    class Meta:
        abstract = True

class AbstractShopMemberRechargeGift(AbstractShopMemberRecharge):
    gift = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        abstract = True

class ShopMemberRecharge(AbstractShopMemberRechargeGift):
    pass

class ShopMemberRechargeSnap(AbstractShopMemberRechargeGift):
    after = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    @classmethod
    def set(cls, recharge, after):
        ectype = {k: v for k, v in recharge.__dict__.items() if not k.startswith('_') and k != 'id'}
        ectype['after'] = after

        return ectype

class AbstractShopMemberRechargeTime(AbstractShopMemberRecharge):
    service = models.ForeignKey(ShopMemberService)

    month = models.IntegerField()

    class Meta:
        abstract = True

class ShopMemberRechargeTime(AbstractShopMemberRechargeTime):
    pass

class ShopMemberRechargeTimeSnap(AbstractShopMemberRechargeTime):
    after = models.DateField(null=True)

    @classmethod
    def set(cls, recharge, after):
        ectype = {k: v for k, v in recharge.__dict__.items() if not k.startswith('_') and k != 'id'}
        ectype['after'] = after

        return ectype

class AbstractShopMemberRechargeCount(AbstractShopMemberRecharge):
    service = models.ForeignKey(ShopMemberService)

    count = models.IntegerField()

    class Meta:
        abstract = True

class ShopMemberRechargeCount(AbstractShopMemberRechargeCount):
    pass

class ShopMemberRechargeCountSnap(AbstractShopMemberRechargeCount):
    after = models.IntegerField(null=True)

    @classmethod
    def set(cls, recharge, after):
        ectype = {k: v for k, v in recharge.__dict__.items() if not k.startswith('_') and k != 'id'}
        ectype['after'] = after

        return ectype

class TradeMemberProfile(AbstractTradeProfile):
    trade = models.OneToOneField(Trade, primary_key=True, related_name='member')
    recharge = models.ForeignKey(ShopMemberRechargeSnap, null=True)
    recharge_time = models.ForeignKey(ShopMemberRechargeTimeSnap, null=True)
    recharge_count = models.ForeignKey(ShopMemberRechargeCountSnap, null=True)

class Festival(models.Model):
    date = models.DateField()

class MarketServer(models.Model):
    name = models.CharField(max_length=32, unique=True)
    shops = models.ManyToManyField(Shop, through='MarketServerShopShip', through_fields=('server', 'shop'))

class MarketServerShopShip(models.Model):
    server = models.ForeignKey(MarketServer, on_delete=models.DO_NOTHING)
    shop = models.ForeignKey(Shop, on_delete=models.DO_NOTHING)

    staff_name = models.CharField(max_length=16, null=True)

    class Meta:
        unique_together = ('server', 'shop')

class MarketServerGroup(models.Model):
    server = models.ForeignKey(MarketServer, on_delete=models.DO_NOTHING)

    name = models.CharField(max_length=32)
    level = models.IntegerField()
    parent = models.ForeignKey('self', null=True, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = ('server', 'name')

class MarketServerEmployeeShip(models.Model):
    group = models.ForeignKey(MarketServerGroup, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(MyUser, on_delete=models.DO_NOTHING)

    name = models.CharField(max_length=32)

    class Meta:
        unique_together = ('group', 'user')
