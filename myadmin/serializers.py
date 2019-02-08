from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from Bankcard.bankcard import verify_bankcard
from SMS import SMS
from RedisIF.RedisIF import RedisIF
from RedisIF.shop import Shop as redis_shop

from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.funtions import timetuple, decimal2string, RandomNumberString
from MyAbstract.serializers import MyModelSerializer
from common.models import Feedback, MyUser, NationalId, Shop, ShopPhoto, ShopActivity, ShopDiscount, \
    ShopWallet, ShopBusinessLicence, ShopLicence, ShopRequire, ShopSpoke, FriendGroup, ShopSpokeGroup, \
    CashRecord, ShopPayZSProfile, ShopBankCard, RandomNickImage, ShopManagerShip, ShopPayFYProfile, MarketServer, \
    MarketServerGroup, MarketServerEmployeeShip
from common.function import register_profile
from common.serializers import ShopLicenceSerializer, ShopBusinessLicenceSerializer


class ShopListSerializer(serializers.ModelSerializer):
    class ManagerInnerSerializer(MyModelSerializer):
        phone = serializers.CharField(source='user.phone_number')

        class Meta:
            model = ShopManagerShip
            fields = ('name', 'phone')

    ico = CompressBase64ImageField()
    state = serializers.SerializerMethodField()
    join_time = serializers.SerializerMethodField()
    sale_month = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    seller_phone = serializers.SerializerMethodField()
    managers = ManagerInnerSerializer(many=True, source='shopmanagership_set')

    def get_state(self, obj):
        return obj.get_state_display()

    def get_join_time(self, obj):
        return timetuple(obj.join_time)

    def get_sale_month(self, obj):
        return decimal2string(obj.sale_month) if hasattr(obj, 'sale_month') else decimal2string(0)

    def get_seller_name(self, obj):
        return obj.seller.nationalid.real_name

    def get_seller_phone(self, obj):
        return obj.seller.phone_number

    class Meta:
        model = Shop
        fields = ('id', 'name', 'address', 'ico', 'phone', 'type', 'join_time', 'state', 'spoke_count',
                  'staff_name', 'sale_month', 'seller_name', 'seller_phone', 'managers')

class ShopPhotoSerializer(serializers.ModelSerializer):
    photo_thumbnail = CompressBase64ImageField()

    class Meta:
        model = ShopPhoto
        fields = ('photo_thumbnail',)

class ShopSerializer(serializers.ModelSerializer):
    class ManagerInnerSerializer(MyModelSerializer):
        class Meta:
            model = ShopManagerShip
            fields = ('name',)

    ico = CompressBase64ImageField()
    face = CompressBase64ImageField()
    business_licence = ShopBusinessLicenceSerializer()
    state = serializers.SerializerMethodField()
    managers = ManagerInnerSerializer(many=True)
    join_time = serializers.SerializerMethodField()
    licences = ShopLicenceSerializer(many=True)
    photos = ShopPhotoSerializer(many=True)

    def get_state(self, obj):
        return obj.get_state_display()

    def get_join_time(self, obj):
        return timetuple(obj.join_time)

    class Meta:
        model = Shop
        fields = ('id', 'name', 'address', 'latitude', 'longitude', 'ico', 'face', 'activity',
                  'discount', 'business_licence', 'phone', 'type', 'describe', 'licences',
                  'open_time', 'close_time', 'convenience', 'state', 'join_time', 'managers', 'photos')

class ShopJudgeSerializer(serializers.Serializer):
    staff = serializers.CharField()
    judge = serializers.BooleanField()

class ShopUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    type = serializers.IntegerField() #1 seller 2 manager 3 seller + manager

class ZSShopSerializer(serializers.Serializer):
    open_id = serializers.CharField(min_length=32, max_length=32)
    open_key = serializers.CharField(min_length=32, max_length=32)
    is_zs_card = serializers.BooleanField()

class PersonCashRecordFilterSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    begin_time = serializers.DateField(required=False)
    end_time = serializers.DateField(required=False)

class PersonCashRecordSerializer(MyModelSerializer):
    username = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()
    user_ico = serializers.SerializerMethodField()
    request_time = serializers.SerializerMethodField()
    handle_time = serializers.SerializerMethodField()
    bank_time = serializers.SerializerMethodField()
    request_acc_no = serializers.SerializerMethodField()

    def get_username(self, obj):
        return obj.user.username

    def get_nick_name(self, obj):
        return obj.user.nick_name

    def get_user_ico(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.user.ico_thumbnail.url)
        return obj.user.ico_thumbnail.url

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    def get_handle_time(self, obj):
        return timetuple(obj.handle_time)

    def get_bank_time(self, obj):
        return timetuple(obj.bank_time)

    def get_request_acc_no(self, obj):
        return obj.request_acc_no[-4:]

    class Meta:
        model = CashRecord
        fields = ('id', 'request_time', 'handle_time', 'bank_time', 'cash', 'status',
                  'username', 'nick_name', 'user_ico', 'request_bank_name', 'request_acc_no')
        custom_fields = ('handle_time', 'bank_time', 'request_bank_name', 'request_acc_no')

class FeedbackSerializer(serializers.ModelSerializer):
    nick_name = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    def get_nick_name(self, obj):
        return obj.user.nick_name

    def get_time(self, obj):
        return timetuple(obj.time)

    class Meta:
        model = Feedback
        fields = ('user_id', 'nick_name', 'time', 'feedback')

class UserFilterSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)

class UserSerializer(MyModelSerializer):
    major_shop = serializers.SerializerMethodField()
    loose_change = serializers.SerializerMethodField()
    have_national = serializers.SerializerMethodField()

    def get_major_shop(self, obj):
        if obj.spoke_profile.major_shop:
            return obj.spoke_profile.major_shop.name

        return None

    def get_loose_change(self, obj):
        return obj.wallet.loose_change()

    def get_have_national(self, obj):
        return hasattr(obj, 'nationalid') and obj.nationalid.is_valid

    class Meta:
        model = MyUser
        fields = ('id', 'nick_name', 'ico_thumbnail', 'abode', 'birthday', 'describe', 'major_shop', 'loose_change', 'have_national', 'username')
        custom_fields = ('birthday', 'major_shop', )

class NationalSerializer(MyModelSerializer):
    national_id_front = Base64ImageField()
    national_id_back = Base64ImageField()

    class Meta:
        model = NationalId
        fields = ('real_name', 'national_id', 'national_id_front', 'national_id_back')

class ShopLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)

class ShopRatioSerializer(serializers.Serializer):
    ratio = serializers.IntegerField()

class DateFilterSerializer(serializers.Serializer):
    begin_time = serializers.DateField(required=False)
    end_time = serializers.DateField(required=False)

class TradeAmountSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    name = serializers.CharField()
    count = serializers.IntegerField()
    sum = serializers.DecimalField(max_digits=8, decimal_places=2)

class TradeDateSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    sum = serializers.DecimalField(max_digits=8, decimal_places=2)

class ShopCreateSerializer(serializers.Serializer):
    class NationalInnerSerializer(serializers.Serializer):
        id  = serializers.CharField()
        name = serializers.CharField()
        front = Base64ImageField()
        back = Base64ImageField()

    class ShopInnerSerializer(MyModelSerializer):
        class ShopLicenceInnerSerializer(serializers.Serializer):
            licence = Base64ImageField()

        class ShopPhotoInnerSerializer(serializers.Serializer):
            photo = Base64ImageField()

        ico = CompressBase64ImageField()
        face = CompressBase64ImageField()
        business_licence = Base64ImageField()
        licences = ShopLicenceInnerSerializer(many=True, required=False)
        photos = ShopPhotoInnerSerializer(many=True, required=False)

        class Meta:
            model = Shop
            fields = ('name', 'address', 'latitude', 'longitude', 'ico', 'face', 'phone', 'type', 'describe',
                      'open_time', 'close_time', 'convenience', 'business_licence', 'licences', 'photos')

        def create(self, validated_data):
            shop = serializers.ModelSerializer.create(self, validated_data)

            return shop

    class ZSPayInnerSerializer(MyModelSerializer):
        class Meta:
            model = ShopPayZSProfile
            fields = ('open_id', 'open_key')

    class FYPayInnerSerializer(MyModelSerializer):
        class Meta:
            model = ShopPayFYProfile
            fields = ('merchant_no', 'terminal_id', 'access_token')

    class ShopBankInnerSerializer(MyModelSerializer):
        class Meta:
            model = ShopBankCard
            fields = ('card', 'name', 'phone')

    username = serializers.CharField()
    national = NationalInnerSerializer(required=False)
    shop = ShopInnerSerializer()
    brokerage = serializers.IntegerField()
    charge = serializers.IntegerField()
    staff = serializers.CharField()

    PAY_TYPE = (
        ('zs', 'zhaoshang'),
        ('fy', 'fuyou'),
        ('other', 'native')
    )

    pay_type = serializers.CharField(max_length=8)

    zs_pay = ZSPayInnerSerializer(required=False)
    bank = ShopBankInnerSerializer(required=False)
    fy_pay = FYPayInnerSerializer(required=False)

    def create_user(self, validated_data):
        user = {}
        user['username'] = validated_data['username']
        temp = RandomNickImage.objects.all().order_by('?')[0]
        user['nick_name'] = temp.nick
        user['ico'] = temp.image
        user['phone_number'] = user['username']
        user = MyUser(**user)
        password = RandomNumberString(6)
        user.set_password(password)
        user.save()
        register_profile(self.request, user)

        return user, password

    def create_nationalid(self, validated_data):
        nationalid = {}
        nationalid['user'] = validated_data['user']
        nationalid['national_id'] = validated_data['id']
        nationalid['real_name'] = validated_data['name']
        nationalid['national_id_front'] = validated_data['front']
        nationalid['national_id_back'] = validated_data['back']

        NationalId.objects.create(**nationalid)

    def create(self, validated_data):
        if 'national' in validated_data:
            national = validated_data.pop('national')
        shop = validated_data.pop('shop')
        brokerage = validated_data.pop('brokerage')
        charge = validated_data.pop('charge')
        staff = validated_data.pop('staff')
        pay_type = validated_data.pop('pay_type')

        if pay_type == 'zs':
            shop.pay_type = 1
            zs_pay = validated_data.pop('zs_pay')
        elif pay_type == 'fy':
            shop.pay_type = 2
            fy_pay = validated_data.pop('fy_pay')
        else:
            # todo
            shop.pay_type = 1
            bank = validated_data.pop('bank')

        pw = None
        try:
            user = MyUser.objects.get(username=validated_data['username'])
        except MyUser.DoesNotExist:
            user, pw = self.create_user(validated_data)

        if not NationalId.objects.filter(pk=user).exists():
            national['user'] = user
            self.create_nationalid(national)

        #shop
        business_licence = shop.pop('business_licence')
        licences = shop.pop('licences') if 'licences' in shop.keys() else None
        photos = shop.pop('photos') if 'photos' in shop.keys() else None
        # todo
        shop = Shop.objects.create(seller=user, state=4, staff_name=staff, charge_ratio=charge, brokerage_type=brokerage, **shop)
        ShopManagerShip.objects.create(shop=shop, user=user, name=user.nationalid.real_name)
        ShopActivity.objects.create(shop=shop)
        ShopDiscount.objects.create(shop=shop, discount=100, full_price=100, reduce_price=0, type=1)
        ShopWallet.objects.create(shop=shop)
        ShopRequire.objects.create(shop=shop)
        RedisIF.r.geoadd('ShopGeo', shop.longitude, shop.latitude, shop.id)
        ShopSpoke.objects.create(shop=shop, spokesman=shop.seller, type='normal')
        group = FriendGroup.objects.get(user=shop.seller, type=3)
        discount = 0.5 * shop.discount.discount + 50 if shop.discount.type == 1 else 0.5 * shop.discount.reduce_price
        ShopSpokeGroup.objects.create(shop=shop, group=group, discount=discount)
        redis_shop.set_charge_ratio(shop.id, shop.charge_ratio)
        redis_shop.set_brokerage_ratio(shop.id, shop.brokerage_ratio)
        ShopBusinessLicence.objects.create(shop=shop, name='tmp', serial_number='123456', valid_date='2020-03-24', business_licence=business_licence)

        if licences:
            for item in licences:
                ShopLicence.objects.create(shop=shop, name='tmp', serial_number='123456', valid_date='2020-03-24', licence=item['licence'])
        
        if photos:
            for item in photos:
                ShopPhoto.objects.create(shop=shop, photo=item['photo'])

        if pay_type == 'zs':
            ShopPayZSProfile.objects.create(shop=shop, **zs_pay)
        elif pay_type == 'fy':
            ShopPayFYProfile.objects.create(shop=shop, **fy_pay)
        else:
            verify = verify_bankcard(bank['card'])

            if not verify[0]:
                verify = (False, 'unknow', 'unknow', 'unknow')

            ShopBankCard.objects.create(wallet=shop.wallet, bank=verify[1], type=verify[2], code=verify[3], **bank)

        if pw:
            SMS.SellerSMS().first_sms(user.username, shop.name, pw)
        else:
            SMS.SellerSMS().create_sms(user.username, shop.name)

        return shop

class MarketServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketServer
        fields = ('id', 'name',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        name = validated_data['name']
        server = MarketServer.objects.create(name=name)
        MarketServerGroup.objects.create(server=server, name=name, level=0)

        return server

class MarketServerManagerCreateSerializer(serializers.Serializer):
    phone = serializers.CharField()
    name = serializers.CharField()
    password = serializers.CharField(required=False)

    def create(self, validated_data):
        phone = validated_data['phone']
        name = validated_data['name']

        try:
            user = MyUser.objects.get(phone_number=phone)
        except MyUser.DoesNotExist:
            try:
                password = validated_data['password']
                temp = RandomNickImage.objects.all().order_by('?')[0]
                user = MyUser(username=phone, nick_name=name, phone_number=phone, ico=temp.image)
                user.set_password(password)
                user.save()
            except:
                raise ValidationDict211Error('error')

        try:
            ship = MarketServerEmployeeShip.objects.create(group_id=validated_data['group_id'], user=user, name=name)
        except:
            raise ValidationDict211Error('已存在管理员')

        return ship