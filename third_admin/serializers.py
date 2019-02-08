import datetime
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.funtions import timetuple, decimal2string, RandomNumberString
from MyAbstract.serializers import MyModelSerializer
from SMS import SMS
from RedisIF.RedisIF import RedisIF
from RedisIF.shop import Shop as redis_shop

from common.models import MyUser, NationalId, Shop, ShopPhoto, ShopActivity, ShopDiscount, \
    ShopWallet, ShopBusinessLicence, ShopLicence, ShopRequire, ShopSpoke, FriendGroup, ShopSpokeGroup, \
    ShopPayFYProfile, ShopBankCard, RandomNickImage, ShopManagerShip, MarketServerShopShip
from common.function import register_profile
from common.serializers import ShopLicenceSerializer, ShopBusinessLicenceSerializer


class ShopFilterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    staff_name = serializers.CharField(required=False)
    begin_time = serializers.DateField(required=False)
    end_time = serializers.DateField(required=False)

    def validate_end_time(self, value):
        value += datetime.timedelta(days=1)

        return value

class ShopListSerializer(serializers.ModelSerializer):
    join_time = serializers.SerializerMethodField()
    seller_name = serializers.CharField(source='seller.nationalid.real_name', read_only=True)
    seller_phone = serializers.CharField(source='seller.phone_number', read_only=True)

    def get_join_time(self, obj):
        return timetuple(obj.join_time)

    class Meta:
        model = Shop
        fields = ('id', 'name', 'address', 'join_time',
                  'staff_name', 'seller_name', 'seller_phone')



class ShopSerializer(serializers.ModelSerializer):
    class ShopPhotoInnerSerializer(serializers.ModelSerializer):
        photo_thumbnail = CompressBase64ImageField()

        class Meta:
            model = ShopPhoto
            fields = ('id', 'photo', 'photo_thumbnail',)

    ico = CompressBase64ImageField()
    face = CompressBase64ImageField()
    business_licence = ShopBusinessLicenceSerializer()
    state = serializers.SerializerMethodField()
    join_time = serializers.SerializerMethodField()
    licences = ShopLicenceSerializer(many=True)
    photos = ShopPhotoInnerSerializer(many=True)

    def get_state(self, obj):
        return obj.get_state_display()

    def get_join_time(self, obj):
        return timetuple(obj.join_time)

    class Meta:
        model = Shop
        fields = ('id', 'name', 'address', 'latitude', 'longitude', 'ico', 'face', 'phone', 'describe', 'licences',
                  'open_time', 'close_time', 'convenience', 'state', 'join_time', 'photos', 'business_licence')

class ShopCreateSerializer(serializers.Serializer):
    class NationalInnerSerializer(serializers.Serializer):
        id = serializers.CharField()
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

    class FYPayInnerSerializer(MyModelSerializer):
        class Meta:
            model = ShopPayFYProfile
            fields = ('merchant_no', 'terminal_id', 'access_token')

    username = serializers.CharField()
    national = NationalInnerSerializer(required=False)
    shop = ShopInnerSerializer()
    charge = serializers.IntegerField()
    staff = serializers.CharField()
    fy_pay = FYPayInnerSerializer()

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
        charge = validated_data.pop('charge')
        staff = validated_data.pop('staff')

        shop.pay_type = 2
        fy_pay = validated_data.pop('fy_pay')

        pw = None
        try:
            user = MyUser.objects.get(username=validated_data['username'])
        except MyUser.DoesNotExist:
            user, pw = self.create_user(validated_data)

        if not NationalId.objects.filter(pk=user).exists():
            national['user'] = user
            self.create_nationalid(national)

        # shop
        business_licence = shop.pop('business_licence')
        licences = shop.pop('licences') if 'licences' in shop.keys() else None
        photos = shop.pop('photos') if 'photos' in shop.keys() else None

        shop = Shop.objects.create(seller=user, state=4, staff_name=staff, charge_ratio=charge,
                                   brokerage_type=2, **shop)
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
        ShopBusinessLicence.objects.create(shop=shop, name='tmp', serial_number='123456', valid_date='2020-03-24',
                                           business_licence=business_licence)

        if licences:
            for item in licences:
                ShopLicence.objects.create(shop=shop, name='tmp', serial_number='123456', valid_date='2020-03-24',
                                           licence=item['licence'])

        if photos:
            for item in photos:
                ShopPhoto.objects.create(shop=shop, photo=item['photo'])

        ShopPayFYProfile.objects.create(shop=shop, **fy_pay)

        MarketServerShopShip.objects.create(shop=shop, server=validated_data['server'], staff_name=validated_data['staff_name'])

        if pw:
            SMS.SellerSMS().first_sms(user.username, shop.name, pw)
        else:
            SMS.SellerSMS().create_sms(user.username, shop.name)

        return shop
