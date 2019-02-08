# coding:utf-8
from django.utils import timezone
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from MyAbstract.serializers import MyModelSerializer
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.funtions import timetuple, decimal2string, liststring_splice
from common.models import MyUser, SmsVerCode, Shop, SpokesmanResume, ShopSpokeRequest, ShopSpoke, Wallet, Trade, Comment, CommentPhoto, \
    ShopRequire, ShopCombo, TradeTicketProfile, TradeRecord, TradeRefund, CashRecord, Party, PartyPerson, PartyMessageBoard, \
    ShopMemberCard, ShopMemberRecharge, ShopMember, ShopDiscount, ShopMemberRechargeTime, ShopMemberRechargeCount, \
    ShopFlyer, ShopFlyerDiscountProfile, ShopFlyerReduceProfile, ShopFlyerExperienceProfile, ShopFlyerExperienceGoods


from common.serializers import ShopPhotoSerializer, ShopComboGoodsSerializer, CardDiscountSerializer, \
    AbstractCashRecordListSerializer, AbstractCashRecordSerializer
from common.function import discount_describe_mine, discount_describe_brother

#no token
class FindPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    verification_code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            ob = SmsVerCode.objects.filter(phone=attrs['username']).order_by('-id')[0]
        except:
            raise ValidationDict211Error('验证码未找到')

        code = ob.code
        expire_time = ob.expire_time

        if code !=attrs['verification_code']:
            raise ValidationDict211Error('验证码不匹配')
        elif expire_time < timezone.now():
            raise ValidationDict211Error('验证码已过期')

        try:
            user = MyUser.objects.get(username=attrs['username'])
        except MyUser.DoesNotExist:
            raise ValidationDict211Error('用户名不存在')
        if not user.is_active:
            raise ValidationDict211Error('该用户被锁定')

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致')

        return attrs

    def save(self, validated_data):
        user = MyUser.objects.get(username=validated_data['username'])
        user.set_password(validated_data['new_password'])
        user.save()
        return user

#have token
class ResetPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=20, min_length=6)
    new_password = serializers.CharField(max_length=20, min_length=6)
    confirm_password = serializers.CharField(max_length=20, min_length=6, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致')
        attrs.pop('confirm_password')
        return attrs

    def save(self, validated_data):
        user = MyUser.objects.get(username=validated_data['username'])
        user.set_password(validated_data['new_password'])
        user.save()
        return user

class FindShopSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    latitude = serializers.DecimalField(max_digits=14, decimal_places=12, required=False)
    longitude = serializers.DecimalField(max_digits=15, decimal_places=12, required=False)
    shop_type = serializers.IntegerField(required=False)
    friend = serializers.BooleanField(required=False)
    shop = serializers.IntegerField(required=False)
    city = serializers.CharField(required=False)

    SEARCH_CHOICES = (
        ('around', 'serach around shops'),
        ('spokes', 'serach shops which spokes'),
        ('name', 'serach shops which name like input'),
        ('nearby', 'serach shops which nearby to visit'),
        ('collect', 'serach shops which are collectd')
    )
    search = serializers.ChoiceField(SEARCH_CHOICES)

class FindShopResponseSerializer(serializers.Serializer):
    address = serializers.SerializerMethodField()

    id = serializers.IntegerField()
    ico = serializers.CharField()
    share = serializers.CharField(required=False)
    discount = serializers.CharField(required=False)
    spokesman_id = serializers.IntegerField()
    spokesman_ico = serializers.CharField()
    name = serializers.CharField()
    level = serializers.DecimalField(max_digits=2, decimal_places=1)
    distance = serializers.IntegerField()
    activity_is_valid = serializers.BooleanField(required=False)
    activity_type = serializers.IntegerField(required=False)
    activity_discount = serializers.IntegerField(required=False)
    activity_full_price = serializers.IntegerField(required=False)
    activity_reduce_price = serializers.IntegerField(required=False)
    discount_is_valid = serializers.BooleanField(required=False)
    discount_type = serializers.IntegerField(required=False)
    discount_discount = serializers.IntegerField(required=False)
    discount_full_price = serializers.IntegerField(required=False)
    discount_reduce_price = serializers.IntegerField(required=False)
    combo = serializers.CharField(required=False)

    def get_address(self, obj):
        return obj.address[obj.address.index('市')+1:]

class ShopWithSpokesSerializer(serializers.Serializer):
    spokesman_id = serializers.IntegerField(required=False)

class ShopComboSketchSerializer(MyModelSerializer):
    class Meta:
        model = ShopCombo
        fields = ('id', 'name', 'ico', 'original_price', 'activity_price')
        read_only_fields = ('id', 'name', 'ico', 'original_price', 'activity_price')

class ShopRetrieveSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    phone = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=14, decimal_places=12)
    longitude = serializers.DecimalField(max_digits=15, decimal_places=12)
    ico = Base64ImageField()
    face = Base64ImageField()
    level = serializers.DecimalField(max_digits=2, decimal_places=1)
    photos = ShopPhotoSerializer(many=True)
    activity = serializers.CharField(required=False)
    discount = serializers.CharField(required=False)
    describe = serializers.CharField()
    open_time = serializers.TimeField()
    close_time = serializers.TimeField()
    convenience = serializers.CharField()
    spokesman_id = serializers.IntegerField()
    spokesman_im_id = serializers.CharField()
    spokesman_name = serializers.CharField()
    spokesman_ico = serializers.CharField()
    spokesman_describe = serializers.CharField()
    comment_count = serializers.IntegerField()
    is_collect = serializers.BooleanField(required=False)
    activity_is_valid = serializers.BooleanField(required=False)
    activity_type = serializers.IntegerField(required=False)
    activity_discount = serializers.IntegerField(required=False)
    activity_full_price = serializers.IntegerField(required=False)
    activity_reduce_price = serializers.IntegerField(required=False)
    discount_is_valid = serializers.BooleanField(required=False)
    discount_type = serializers.IntegerField(required=False)
    discount_discount = serializers.IntegerField(required=False)
    discount_full_price = serializers.IntegerField(required=False)
    discount_reduce_price = serializers.IntegerField(required=False)
    combo = ShopComboSketchSerializer(many=True)
    is_spokes = serializers.BooleanField()
    has_member = serializers.BooleanField()
    is_member = serializers.BooleanField(required=False)
    announcement = serializers.CharField()

class ShopComboSerializer(MyModelSerializer):
    ico = CompressBase64ImageField()
    goods = ShopComboGoodsSerializer(many=True)

    spokesman_id = serializers.SerializerMethodField()
    spokesman_ico = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    shop_address = serializers.SerializerMethodField()
    shop_phone = serializers.SerializerMethodField()

    def get_spokesman_id(self, obj):
        return obj.spokesman_id

    def get_spokesman_ico(self, obj):
        return obj.spokesman_ico

    def get_shop_name(self, obj):
        return obj.shop_name

    def get_shop_address(self, obj):
        return obj.shop_address

    def get_shop_phone(self, obj):
        return obj.shop_phone

    class Meta:
        model = ShopCombo
        fields = ('id', 'name', 'ico', 'original_price', 'activity_price', 'valid_period_begin',
                  'valid_period_end', 'use_time', 'precautions', 'tips', 'goods', 'spokesman_id', 'spokesman_ico',
                  'shop_name', 'shop_address', 'shop_phone')
        read_only_fields = ('id', 'name', 'ico', 'original_price', 'activity_price', 'valid_period_begin',
                  'valid_period_end', 'use_time', 'precautions', 'tips', 'goods', 'spokesman_id', 'spokesman_ico',
                  'shop_name', 'shop_address', 'shop_phone')

class ShopInfo1Serializer(MyModelSerializer):
    class Meta:
        model = Shop
        fields = ('name', 'face')

class ShopSimpleSerializer(serializers.Serializer):
    activity = serializers.CharField(required=False)
    discount = serializers.CharField(required=False)
    spokesman_id = serializers.IntegerField()
    spokesman_ico = serializers.CharField()

class ShopSerializer(serializers.ModelSerializer):
    ico = serializers.SerializerMethodField()

    def get_ico(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.ico_thumbnail.url)
        return obj.ico_thumbnail.url

    class Meta:
        model = Shop
        fields = ('name', 'address', 'latitude', 'longitude', 'ico', 'business_licence', 'phone', 'type',
                  'level', 'describe')
        read_only_fields = ('ico',)

class ShopRequireSerializer(MyModelSerializer):
    describe = serializers.SerializerMethodField()

    def get_describe(self, obj):
        discount = ShopDiscount.objects.get(shop=obj.shop)
        mine = discount_describe_mine(**discount.__dict__)
        temp, brother = discount_describe_brother(**discount.__dict__)
        describe = liststring_splice((('个人优惠：'+mine), ('挚友优惠:'+brother))) if mine and brother else ''
        return describe if '' != describe else None

    class Meta:
        model = ShopRequire
        fields = ('require1', 'require2', 'require3', 'describe')
        custom_fields = ('describe',)

class ShopMemberInfoSerializer(serializers.Serializer):
    shop_name = serializers.CharField()
    has_member = serializers.BooleanField()
    image = serializers.CharField(required=False)
    is_member = serializers.BooleanField(required=False)
    loose_change = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    has_trade_password = serializers.BooleanField(required=False)

class ShopRequire2Serializer(serializers.ModelSerializer):
    ico = serializers.SerializerMethodField()

    def get_ico(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.ico_thumbnail.url)
        return obj.ico_thumbnail.url

    require = ShopRequireSerializer()

    class Meta:
        model = Shop
        fields = ('name', 'address', 'ico', 'phone', 'require')

class SpokesmanResumeSerializer(serializers.ModelSerializer):
    real_name = serializers.SerializerMethodField()

    def get_real_name(self, obj):
        return obj.user.nationalid.real_name if hasattr(obj.user, 'nationalid') else None

    class Meta:
        model = SpokesmanResume
        fields = ('work', 'resume', 'real_name')

class ShopSpokesRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopSpokeRequest
        fields = ('request', )

class ShopSpokeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopSpoke
        fields = ('shop', 'begin_time')
        read_only_fields = ('shop', 'begin_time')

class ShopBusinessLicencesSerializer(serializers.Serializer):
    business_licence = Base64ImageField()

class ShopLicencesSerializer(serializers.Serializer):
    licences = serializers.ListField(serializers.CharField())

class CompleteTradeSerializer(serializers.Serializer):
    spokesman = serializers.IntegerField()
    discount_price = serializers.DecimalField(max_digits=8, decimal_places=2)
    constant_price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    client_price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    ticket_number = serializers.CharField(required=False)

class TradeCalculateSerializer(serializers.Serializer):
    activity_reduce = serializers.DecimalField(max_digits=8, decimal_places=2)
    discount_reduce = serializers.DecimalField(max_digits=8, decimal_places=2)
    trade_price = serializers.DecimalField(max_digits=8, decimal_places=2)

class CompleteTradeComboSerializer(serializers.Serializer):
    spokesman = serializers.IntegerField()
    count = serializers.IntegerField()
    client_price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)

class TradeComboCalculateSerializer(serializers.Serializer):
    discount_reduce = serializers.DecimalField(max_digits=8, decimal_places=2)
    trade_price = serializers.DecimalField(max_digits=8, decimal_places=2)

class WeiXinPublicAccountTradeSerializer(serializers.Serializer):
    spokesman = serializers.IntegerField()
    discount_price = serializers.DecimalField(max_digits=8, decimal_places=2)
    constant_price = serializers.DecimalField(max_digits=8, decimal_places=2)
    client_price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    ip = serializers.IPAddressField(required=False)
    openid = serializers.CharField(required=False)
    pay_password = serializers.CharField(required=False)

class WeiXinPublicAccountTradeComboSerializer(serializers.Serializer):
    spokesman = serializers.IntegerField()
    count = serializers.IntegerField()
    client_price = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    ip = serializers.IPAddressField(required=False)
    openid = serializers.CharField(required=False)
    pay_password = serializers.CharField(required=False)

class CommentPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentPhoto
        fields = ('photo', 'photo_thumbnail')

class ShopCommentSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()
    user_ico = serializers.SerializerMethodField()
    photos = CommentPhotoSerializer(many=True)
    time = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.trade.id

    def get_nick_name(self, obj):
        return obj.trade.buyer.nick_name

    def get_user_ico(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.trade.buyer.ico_thumbnail.url)
        return obj.trade.buyer.ico_thumbnail.url

    def get_time(self, obj):
        return timetuple(obj.time)

    def get_grade(self, obj):
        return obj.trade.grade

    class Meta:
        model = Comment
        fields = ('id', 'time', 'comment', 'photos', 'nick_name', 'user_ico', 'grade')
        read_only_fields = ('id', 'time', 'comment', 'photos', 'nick_name', 'user_ico', 'grade')

class TradeBuyerListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    ico = serializers.SerializerMethodField()
    trade_time = serializers.SerializerMethodField()

    def get_name(self, obj):
        if obj.profile_type == 'ticket':
            for item in obj.tickets.all():
                return item.combo.name
        else:
            return obj.shop.name

    def get_ico(self, obj):
        request = self.context.get('request', None)
        if obj.profile_type == 'ticket':
            for item in obj.tickets.all():
                if request is not None:
                    return request.build_absolute_uri(item.combo.ico_thumbnail.url)
                return item.combo.ico_thumbnail.url
        else:
            if request is not None:
                return request.build_absolute_uri(obj.shop.ico_thumbnail.url)
            return obj.shop.ico_thumbnail.url

    def get_trade_time(self, obj):
        return timetuple(obj.trade_time)

    class Meta:
        model = Trade
        fields = ('name', 'ico', 'trade_number', 'trade_price', 'trade_time')

class TicketTempSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeTicketProfile
        fields = ('ticket_number', 'status')

class TradeBuyerSerializer(MyModelSerializer):
    shop_name = serializers.SerializerMethodField()
    ico = serializers.SerializerMethodField()
    trade_time = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()

    activity = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()

    tickets = TicketTempSerializer(many=True, required=False)

    member_loose_change = serializers.SerializerMethodField()

    def get_shop_name(self, obj):
        return obj.shop.name

    def get_ico(self, obj):
        request = self.context.get('request', None)
        if obj.profile_type == 'ticket':
            for item in obj.tickets.all():
                if request is not None:
                    return request.build_absolute_uri(item.combo.ico_thumbnail.url)
                return item.combo.ico_thumbnail.url
        else:
            if request is not None:
                return request.build_absolute_uri(obj.shop.ico_thumbnail.url)
            return obj.shop.ico_thumbnail.url

    def get_trade_time(self, obj):
        return timetuple(obj.trade_time)

    def get_grade(self, obj):
        return obj.grade if obj.grade else 0

    def get_type(self, obj):
        return obj.profile_type

    def get_activity(self, obj):
        if obj.profile_type == 'discount' and obj.tradediscountprofile.activity:
            return '商家活动' + obj.tradediscountprofile.activity

    def get_discount(self, obj):
        if obj.discount:
            return '好友独享' + obj.discount
        elif 'member'==obj.profile_type:
            # Todo have three choice
            if obj.member.recharge:
                return obj.member.recharge.gift

        return None

    def get_combo_name(self, obj):
        if obj.profile_type == 'ticket':
            for item in obj.tickets.all():
                return item.combo.name

    def get_member_loose_change(self, obj):
        if obj.profile_type == 'member':
            # Todo have three choice
            if obj.member.recharge:
                return decimal2string(obj.member.recharge.after)

    class Meta:
        model = Trade
        fields = ('trade_number', 'activity', 'discount', 'trade_price', 'trade_time', 'type',
                  'shop_name', 'ico', 'grade', 'total_fee', 'combo_name', 'tickets', 'member_loose_change')
        read_only_fields = ('trade_number', 'activity', 'discount', 'trade_price', 'trade_time', 'type',
                            'shop_name', 'ico', 'grade', 'total_fee', 'combo_name',  'tickets', 'member_loose_change')
        custom_fields = ('discount', 'activity', 'combo_name', 'member_loose_change')

class TradeSpokesmanSerializer(serializers.ModelSerializer):
    shop_name = serializers.SerializerMethodField()
    shop_ico = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()
    trade_time = serializers.SerializerMethodField()
    brokerage = serializers.SerializerMethodField()

    def get_shop_name(self, obj):
        return obj.trade.shop.name if obj.trade else obj.ticket.trade.shop.name

    def get_shop_ico(self, obj):
        url = obj.trade.shop.ico_thumbnail.url if obj.trade else obj.ticket.trade.shop.ico_thumbnail.url

        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_nick_name(self, obj):
        return obj.trade.buyer.nick_name if obj.trade else obj.ticket.trade.buyer.nick_name

    def get_trade_time(self, obj):
        return timetuple(obj.time)

    def get_brokerage(self, obj):
        return obj.trade.tradediscountprofile.brokerage if obj.trade else obj.ticket.brokerage

    class Meta:
        model = TradeRecord
        fields = ('id', 'confirm', 'brokerage', 'trade_time', 'shop_name', 'shop_ico', 'nick_name')
        read_only_fields = ('id', 'confirm', 'brokerage', 'trade_time', 'shop_name', 'shop_ico', 'nick_name')

class TradeRefundListSerializer(serializers.ModelSerializer):
    request_time = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()
    combo_ico = serializers.SerializerMethodField()

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    def get_combo_name(self, obj):
        for item in obj.trade.tickets.all():
            return item.combo.name

    def get_combo_ico(self, obj):
        url = ''
        for item in obj.trade.tickets.all():
            url = item.combo.ico_thumbnail.url
            break

        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    class Meta:
        model = TradeRefund
        fields = ('id', 'request_time', 'combo_name', 'combo_ico', 'amount', 'status')

class TradeRefundSerializer(MyModelSerializer):
    request_time = serializers.SerializerMethodField()
    refund_time = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    trade_number = serializers.SerializerMethodField()

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    def get_refund_time(self, obj):
        if obj.refund_time:
            return timetuple(obj.refund_time)

    def get_count(self, obj):
        return obj.tickets.count()

    def get_platform(self, obj):
        pay_types = obj.trade.pay_type()

        if 'weixin' in pay_types or 'weixinjs' in pay_types or 'zb_wx' in pay_types:
            platform = '微信'
        elif 'ali' in pay_types or 'zb_ali' in pay_types:
            platform = '支付宝'
        elif 'zhaobank' in pay_types:
            platform = '一网通'
        elif 'member' in pay_types:
            platform = '会员卡'

        return platform

    def get_phone(self, obj):
        pay_types = obj.trade.pay_type()

        if 'weixin' in pay_types or 'weixinjs' in pay_types or 'zb_wx' in pay_types:
            phone_number = '110'
        elif 'ali' in pay_types or 'zb_ali' in pay_types:
            phone_number = '911'
        elif 'zhaobank' in pay_types:
            phone_number = '315'
        elif 'member' in pay_types:
            phone_number = '000'

        return phone_number

    def get_trade_number(self, obj):
        for item in obj.trade.tradepay_set.all():
            return obj.trade.trade_number

    class Meta:
        model = TradeRefund
        fields = ('id', 'request_time', 'refund_time', 'count', 'amount', 'status', 'platform', 'phone', 'trade_number')
        custom_fields = ('refund_time',)

class TradeAvailableSerializer(serializers.ModelSerializer):
    shop_name = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()
    combo_ico = serializers.SerializerMethodField()
    valid_period = serializers.SerializerMethodField()
    ticket_price = serializers.SerializerMethodField()
    tickets = serializers.SerializerMethodField()

    def get_shop_name(self, obj):
        return obj.shop.name

    def get_combo_name(self, obj):
        return obj.tickets.all()[0].combo.name

    def get_combo_ico(self, obj):
        url = obj.tickets.all()[0].combo.ico_thumbnail.url

        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_valid_period(self, obj):
        return obj.tickets.all()[0].combo.valid_period_end

    def get_ticket_price(self, obj):
        return decimal2string(obj.tickets.all()[0].trade_price)

    def get_tickets(self, obj):
        return TicketTempSerializer(obj.temp, many=True).data

    class Meta:
        model = Trade
        fields = ('trade_number', 'shop_name', 'combo_name', 'combo_ico', 'valid_period', 'ticket_price', 'tickets')

class TradeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.trade_number

    class Meta:
        model = Trade
        fields = ('id', 'shop', 'buyer', 'spokesman', 'activity', 'discount', 'discount_price',
                  'constant_price', 'trade_price', 'brokerage', 'trade_time', 'grade', 'state')
        read_only_fields = ('id', 'shop', 'buyer', 'spokesman', 'activity', 'discount', 'discount_price',
                  'constant_price', 'trade_price', 'brokerage', 'trade_time', 'grade', 'state')

class CommentPhotoCreateSerializer(serializers.ModelSerializer):
    photo = CompressBase64ImageField()

    class Meta:
        model = CommentPhoto
        fields = ('comment', 'photo')
        read_only_fields = ('comment')

class CommentCreateSerializer(serializers.Serializer):
    grade = serializers.IntegerField()
    comment = serializers.CharField(required=False)
    photos = serializers.ListField(child=serializers.CharField(), required=False)

    def create(self, validated_data):
        validated_data.pop('grade')

        comment = None
        photos = []
        if 'photos' in validated_data:
            photos = validated_data.pop('photos')

            if 'comment' not in validated_data:
                comment = ''

        if 'comment' in validated_data:
            comment = validated_data['comment']

        if comment:
            comment = Comment.objects.create(trade=validated_data['trade'], comment=comment)

        if len(photos) > 0:
            comment = Comment.objects.create(trade=validated_data['trade'], comment='')

        for item in photos:
            serializer = CommentPhotoCreateSerializer(data={'photo': item})
            serializer.is_valid(raise_exception=True)
            serializer.save(comment=comment)

        return comment

class CollectShopSerializer(serializers.Serializer):
    is_collect = serializers.BooleanField()

class WalletLooseChangeSerializer(serializers.ModelSerializer):
    loose_change = serializers.SerializerMethodField()
    remain_cash = serializers.SerializerMethodField()
    no_cash = serializers.SerializerMethodField()
    have_pay_pw = serializers.SerializerMethodField()
    have_bankcard = serializers.SerializerMethodField()
    already_settled = serializers.SerializerMethodField()
    will_settle = serializers.SerializerMethodField()

    def get_loose_change(self, obj):
        return str(obj.loose_change())

    def get_remain_cash(self, obj):
        return str(obj.remain_cash())

    def get_no_cash(self, obj):
        return str(obj.no_cash())

    def get_have_pay_pw(self, obj):
        return obj.has_usable_password()

    def get_have_bankcard(self, obj):
        return hasattr(obj, 'bankcard') and obj.bankcard.is_valid

    def get_already_settled(self, obj):
        return 0

    def get_will_settle(self, obj):
        return 0

    class Meta:
        model = Wallet
        fields = ('loose_change', 'remain_cash', 'no_cash', 'have_pay_pw', 'have_bankcard',
                  'already_settled', 'will_settle')

class CashSerializer(serializers.Serializer):
    pay_password = serializers.CharField()

class FriendSpokesShopSerializer(serializers.Serializer):
    name = serializers.CharField()
    ico = serializers.CharField()

class FriendDetailSerializer(serializers.Serializer):
    name = serializers.CharField()
    alias = serializers.CharField(required=False)
    ico = serializers.CharField()
    major_type = serializers.IntegerField(required=False)
    group_name = serializers.CharField(required=False)
    shops = FriendSpokesShopSerializer(many=True)

class FriendSpokesShopDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    custom_type = serializers.CharField(required=False)
    describe = serializers.CharField(allow_blank=True)
    ico = serializers.CharField()
    level = serializers.DecimalField(max_digits=4, decimal_places=2)
    type = serializers.IntegerField()
    spokesman_id = serializers.IntegerField()
    spokesman_ico = serializers.CharField()
    share = serializers.CharField(required=False)
    discount = serializers.CharField(required=False)

class SpokesShopSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ico = serializers.CharField()
    name = serializers.CharField()
    address = serializers.CharField()
    type = serializers.IntegerField()
    custom_type = serializers.CharField(required=False)
    level = serializers.DecimalField(max_digits=4, decimal_places=2)
    describe = serializers.CharField(allow_blank=True)
    activity = serializers.CharField(required=False)
    discount_type = serializers.IntegerField(required=False)
    discount = serializers.IntegerField(required=False)
    full_price = serializers.IntegerField(required=False)
    reduce_price = serializers.IntegerField(required=False)
    bonus = serializers.IntegerField(required=False)
    friend_discount = serializers.IntegerField(required=False)
    major = serializers.BooleanField(required=False)
    spokesman_id = serializers.IntegerField()

class SpokesShopRequestListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ico = serializers.CharField()
    name = serializers.CharField()
    address = serializers.CharField()
    type = serializers.IntegerField()
    custom_type = serializers.CharField(required=False)
    level = serializers.DecimalField(max_digits=4, decimal_places=2)
    describe = serializers.CharField(allow_blank=True)
    require1 = serializers.CharField()
    require2 = serializers.CharField()
    require3 = serializers.CharField()
    request_time = serializers.DateField()
    handle_time = serializers.DateField(required=False)
    result = serializers.CharField()

class SpokesShopGroupDiscountSerializer(serializers.Serializer):
    discount = serializers.IntegerField()

class ThirdAuthSerializer(serializers.Serializer):
    weixin = serializers.BooleanField(required=False)
    qq = serializers.BooleanField(required=False)
    weibo = serializers.BooleanField(required=False)
    zhifubao = serializers.BooleanField(required=False)

class Interface1Serializer(serializers.Serializer):
    nick = serializers.CharField()
    ico = CompressBase64ImageField()
    describe = serializers.CharField()
    loose_change = serializers.DecimalField(max_digits=10, decimal_places=2)
    have_pay_pw = serializers.BooleanField()
    have_bankcard = serializers.BooleanField()
    have_national_id = serializers.BooleanField()
    no_disturb = serializers.BooleanField()
    available_tickets = serializers.IntegerField()
    third_auth = ThirdAuthSerializer(required=False)

class ShopShareUrlSerializer(serializers.Serializer):
    spokesman_id = serializers.IntegerField()

class TradeTicketProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeTicketProfile
        fields = ('ticket_number',)

class TradeResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    ico = serializers.CharField()

class TradeComboResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    ico = serializers.CharField()
    name = serializers.CharField()
    discount_reduce = serializers.DecimalField(max_digits=10, decimal_places=2)

class RefundTicketSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    reason = serializers.CharField()

class BindBankcardSerializer(serializers.Serializer):
    card_name = serializers.CharField()
    master_name = serializers.CharField()
    phone = serializers.CharField()
    verification_code = serializers.CharField()
    pay_password = serializers.CharField()

    def validate(self, attrs):
        try:
            obj = SmsVerCode.objects.filter(phone=attrs['phone']).order_by('-id')[0]
        except:
            raise ValidationDict211Error('验证码未找到.')

        code = obj.code
        expire_time = obj.expire_time

        if code !=attrs['verification_code']:
            raise ValidationDict211Error('验证码不匹配.')
        elif expire_time < timezone.now():
            raise ValidationDict211Error('验证码已过期.')

        obj.obsolete = True
        obj.save(update_fields=['obsolete'])

        return attrs

class SearchFriendSerializer(serializers.Serializer):
    search = serializers.CharField()

class FriendListSerializer(serializers.ModelSerializer):
    im_account = serializers.SerializerMethodField()
    major_type = serializers.SerializerMethodField()

    def get_im_account(self, obj):
        return str(obj.id)

    def get_major_type(self, obj):
        return obj.spoke_profile.major_shop.type.name if obj.spoke_profile.major_shop else ''

    class Meta:
        model = MyUser
        fields = ('im_account', 'nick_name', 'ico_thumbnail', 'major_type')

class PartyPersonSerializer(MyModelSerializer):
    im_id = serializers.SerializerMethodField()
    nick_name = serializers.SerializerMethodField()
    ico_thumbnail = serializers.SerializerMethodField()
    join_time = serializers.SerializerMethodField()

    def get_im_id(self, obj):
        return obj.user.id

    def get_nick_name(self, obj):
        return obj.user.nick_name

    def get_ico_thumbnail(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.user.ico_thumbnail.url)
        return obj.user.ico_thumbnail.url

    def get_join_time(self, obj):
        return timetuple(obj.join_time)

    class Meta:
        model = PartyPerson
        fields = ('im_id', 'nick_name', 'ico_thumbnail', 'remark', 'join_time', 'person_count', 'remark')
        custom_fields = ('remark',)

class PartyCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Party
        fields = ('name', 'describe', 'begin_time', 'end_time', 'location', 'latitude', 'longitude', 'image',
                  'max_persons', 'location_detail')

class PartySerializer(MyModelSerializer):
    image = Base64ImageField()
    organizer_nick = serializers.SerializerMethodField()
    begin_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    persons = serializers.SerializerMethodField()
    person_count = serializers.SerializerMethodField()
    has_joined = serializers.SerializerMethodField()
    is_organizer = serializers.SerializerMethodField()

    def get_organizer_nick(self, obj):
        return obj.organizer.nick_name

    def get_begin_time(self, obj):
        return timetuple(obj.begin_time)

    def get_end_time(self, obj):
        return timetuple(obj.end_time)

    def get_persons(self, obj):
        return PartyPersonSerializer(obj.persons.all().order_by('-id')[0:3], many=True, context=self.context).data

    def get_person_count(self, obj):
        count = 0

        for person in obj.persons.all():
            count += person.person_count

        return count

    def get_has_joined(self, obj):
        return obj.has_joined

    def get_is_organizer(self, obj):
        return obj.is_organizer

    class Meta:
        model = Party
        fields = ('name', 'describe', 'begin_time', 'end_time', 'location', 'latitude', 'longitude', 'image',
                  'persons', 'person_count', 'organizer_nick', 'has_joined', 'status', 'is_organizer',
                  'max_persons', 'location_detail')
        read_only_fields = ('persons',)
        custom_fields = ('max_persons', 'location_detail')

class PartyListSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    image_thumbnail = Base64ImageField()
    begin_time = serializers.SerializerMethodField()
    organizer_ico = serializers.SerializerMethodField()
    person_count = serializers.SerializerMethodField()

    def get_begin_time(self, obj):
        return timetuple(obj.begin_time)

    def get_organizer_ico(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.organizer.ico_thumbnail.url)
        return obj.organizer.ico_thumbnail.url

    def get_person_count(self, obj):
        count = 0

        for person in obj.persons.all():
            count += person.person_count

        return count

    class Meta:
        model = Party
        fields = ('id', 'name', 'describe', 'begin_time', 'location', 'image','image_thumbnail',
                  'organizer_ico', 'person_count')

class PartyJoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartyPerson
        fields = ('remark', 'person_count')

class PartyMessageBoardSerializer(MyModelSerializer):
    im_id = serializers.SerializerMethodField()
    user_nick = serializers.SerializerMethodField()
    user_ico = serializers.SerializerMethodField()
    reply_nick = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    def get_im_id(self, obj):
        return obj.user.id

    def get_user_nick(self, obj):
        return obj.user.nick_name

    def get_user_ico(self, obj):
        url = obj.user.ico_thumbnail.url

        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_reply_nick(self, obj):
        if obj.reply_id:
            return PartyMessageBoard.objects.get(pk=obj.reply_id).user.nick_name
        return None

    def get_time(self, obj):
        return timetuple(obj.time)

    class Meta:
        model = PartyMessageBoard
        fields = ('id', 'im_id', 'user_nick', 'user_ico', 'time', 'message', 'reply_id', 'reply_nick')
        read_only_fields = ('id', 'im_id', 'user_nick', 'user_ico', 'time', 'reply_nick')
        custom_fields = ('reply_id', 'reply_nick',)

class ShopMemberCardSerializer(MyModelSerializer):
    image = Base64ImageField()
    discount = CardDiscountSerializer()
    shop_name = serializers.SerializerMethodField()
    describe = serializers.SerializerMethodField()

    def get_shop_name(self, obj):
        return obj.shop.name

    def get_describe(self, obj):
        describe = obj.describe
        if hasattr(obj, 'discount'):
            mine = discount_describe_mine(True, **obj.discount.__dict__)
            if mine:
                if '' != describe:
                    describe += ','
                describe += ('个人优惠：' + mine)

            temp, brother = discount_describe_brother(True, **obj.discount.__dict__)
            if brother:
                if '' != describe:
                    describe += '\n'
                describe += ('挚友优惠：' + brother)

        return describe if '' != describe else None

    class Meta:
        model = ShopMemberCard
        fields = ('id', 'name', 'image', 'discount', 'describe', 'shop_name')
        read_only_fields = ('id', )
        custom_fields = ('discount', 'describe')

class ShopMemberRechargeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopMemberRecharge
        fields = ('id', 'member_card', 'recharge', 'gift')
        read_only_fields = ('id', )

class ShopMemberRechargeTimeSerializer(MyModelSerializer):
    member_card_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()

    def get_member_card_name(self, obj):
        return obj.member_card.name

    def get_service_name(self, obj):
        return obj.service.name

    class Meta:
        model = ShopMemberRechargeTime
        fields = ('id', 'member_card', 'member_card_name', 'recharge', 'service', 'service_name', 'month')
        read_only_fields = ('id', 'member_card_name', 'service_name')

class ShopMemberRechargeCountSerializer(serializers.ModelSerializer):
    member_card_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()

    def get_member_card_name(self, obj):
        return obj.member_card.name

    def get_service_name(self, obj):
        return obj.service.name

    class Meta:
        model = ShopMemberRechargeCount
        fields = ('id', 'member_card', 'member_card_name', 'recharge', 'service', 'service_name', 'count')
        read_only_fields = ('id', 'member_card_name', 'service_name')

class ShopMemberRechargeAllSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    member_card = serializers.IntegerField()
    member_card_name = serializers.CharField()
    recharge = serializers.CharField()
    service_name = serializers.CharField()
    describe = serializers.CharField()

    TYPE = (
        ('gift', '冲送'),
        ('time', '时间'),
        ('count', '次数')
    )

    type = serializers.CharField(max_length=8)

    def set(self, id, member_card, member_card_name, recharge, service_name, describe, type):
        self.id = id
        self.member_card = member_card
        self.member_card_name = member_card_name
        self.recharge = recharge
        self.service_name = service_name
        self.describe = describe
        self.type = type

class ShopMemberListSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    shop_name = serializers.CharField()
    image = serializers.CharField()
    card_name = serializers.CharField()
    number = serializers.CharField()

class ShopMemberSerializer(MyModelSerializer):
    discount = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    card_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    number = serializers.SerializerMethodField()
    describe = serializers.SerializerMethodField()

    def get_discount(self, obj):
        if hasattr(obj.member_card, 'discount'):
            return obj.member_card.discount.discount
        else:
            return 100

    def get_shop_name(self, obj):
        return obj.shop.name

    def get_card_name(self, obj):
        return obj.member_card.name

    def get_image(self, obj):
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(obj.member_card.image.url)
        return obj.member_card.image.url

    def get_number(self, obj):
        return str(obj.id)

    def get_describe(self, obj):
        card = obj.member_card
        describe = card.describe
        if hasattr(card, 'discount'):
            mine = discount_describe_mine(True, **card.discount.__dict__)
            if mine:
                if '' != describe:
                    describe += ','
                describe += ('个人优惠：' + mine)

            temp, brother = discount_describe_brother(True, **card.discount.__dict__)
            if brother:
                if '' != describe:
                    describe += '\n'
                describe += ('挚友优惠：' + brother)

        return describe if '' != describe else None

    class Meta:
        model = ShopMember
        fields = ('loose_change', 'discount', 'shop_name', 'card_name', 'image', 'number', 'describe')
        custom_fields = ('discount', 'describe')

class TradeMemberSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    recharge_id = serializers.IntegerField()

class HasPhoneSerializer(serializers.Serializer):
    flag = serializers.BooleanField()
    phone_number = serializers.CharField(required=False)

class CashRecordListSerializer(AbstractCashRecordListSerializer):
    class Meta:
        model = CashRecord
        fields = ('id', 'request_time', 'cash', 'status')

class CashRecordSerializer(AbstractCashRecordSerializer):
    class Meta:
        model = CashRecord
        fields = ('id', 'cash', 'charge', 'status', 'trace',
                  'request_bank_name', 'request_acc_no')

class TradeIntroSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    spoker_id = serializers.IntegerField()
    has_pay = serializers.BooleanField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    discount = serializers.DecimalField(max_digits=8, decimal_places=2)

class PaySerializer(serializers.Serializer):
    pay_type = serializers.IntegerField()
    pay_password = serializers.CharField(required=False)
    fy_wx_openid = serializers.CharField(required=False)

class ShopFlyerProfileMineSerializer(serializers.Serializer):
    ticket_number = serializers.CharField()
    type = serializers.IntegerField()
    discount = serializers.IntegerField(required=False)
    full_price = serializers.IntegerField(required=False)
    reduce_price = serializers.IntegerField(required=False)
    describe = serializers.CharField()

class TradeGetFlyerSerializer(serializers.Serializer):
    trade_number = serializers.CharField(required=False)
    latitude = serializers.DecimalField(max_digits=14, decimal_places=12, required=False)
    longitude = serializers.DecimalField(max_digits=15, decimal_places=12, required=False)

class ShopFlyerSerializer(MyModelSerializer):
    img = CompressBase64ImageField()
    shop_id = serializers.IntegerField(source='shop.id')
    combo_name = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    ticket_number = serializers.SerializerMethodField()
    is_new = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    full_price = serializers.SerializerMethodField()
    reduce_price = serializers.SerializerMethodField()

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'img', 'valid_period_end', 'combo_name', 'shop_id', 'shop_name',
                  'ticket_number', 'is_new', 'distance', 'discount', 'full_price', 'reduce_price')
        custom_fields = ('combo_name', 'shop_name', 'ticket_number',
                         'is_new', 'distance', 'discount', 'full_price', 'reduce_price')

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

    def get_shop_name(self, obj):
        return obj.shop.name if 3 != obj.type else None

    def get_ticket_number(self, obj):
        return obj.ticket_number if hasattr(obj, 'ticket_number') else None

    def get_is_new(self, obj):
        return obj.is_new if hasattr(obj, 'is_new') else None

    def get_distance(self, obj):
        return obj.distance if hasattr(obj, 'distance') else None

    def get_discount(self, obj):
        return obj.discount.discount if 1 == obj.type else None

    def get_full_price(self, obj):
        return obj.reduce.full_price if 2 == obj.type else None

    def get_reduce_price(self, obj):
        return obj.reduce.reduce_price if 2 == obj.type else None

class ShopFlyerInnerSerializer(MyModelSerializer):
    img = CompressBase64ImageField()
    describe = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()

    shop_id = serializers.IntegerField(source='shop.id')
    shop_name = serializers.CharField(source='shop.name')
    address = serializers.CharField(source='shop.address')
    phone = serializers.CharField(source='shop.phone')

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'img', 'valid_period_end', 'describe', 'combo_name',
                  'shop_id', 'shop_name', 'address', 'phone',
                  'day_begin', 'day_end', 'festival', 'precautions', 'tips')
        custom_fields = ('combo_name', )

    def get_describe(self, obj):
        if 1 == obj.type:
            return '店内消费{0}折'.format(obj.discount.discount / 10)
        elif 2 == obj.type:
            return '店内消费满{0}减{1}'.format(obj.reduce.full_price, obj.reduce.reduce_price)
        elif 3 == obj.type:
            return '原价: {0}'.format(obj.experience.original_price)

        return None

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

class ShopFlyerDiscountProfileSerializer(serializers.ModelSerializer):
    flyer = ShopFlyerInnerSerializer()

    class Meta:
        model = ShopFlyerDiscountProfile
        fields = ('flyer', 'discount', 'full_price')

class ShopFlyerReduceProfileSerializer(serializers.ModelSerializer):
    flyer = ShopFlyerInnerSerializer()

    class Meta:
        model = ShopFlyerReduceProfile
        fields = ('flyer', 'full_price', 'reduce_price')

class ShopFlyerExperienceGoodsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopFlyerExperienceGoods
        fields = ('id', 'name', 'price', 'num', 'unit')

class ShopFlyerExperienceProfileSerializer(serializers.ModelSerializer):
    flyer = ShopFlyerInnerSerializer()
    goods = ShopComboGoodsSerializer(many=True)

    class Meta:
        model = ShopFlyerExperienceProfile
        fields = ('flyer', 'name', 'original_price', 'goods')

class ShopBuyParaSerializer(serializers.Serializer):
    name = serializers.CharField()
    activity = serializers.CharField(required=False)
    discount = serializers.CharField(required=False)
    spokesman_id = serializers.IntegerField()
    spokesman_ico = serializers.CharField()
    shop_ico = serializers.ImageField(required=False)
    is_member = serializers.BooleanField(required=False)
    loose_change = serializers.CharField(required=False)
    has_trade_password = serializers.BooleanField(required=False)

    flyers = ShopFlyerProfileMineSerializer(many=True, required=False)

class BuyerFilterSerializer(serializers.Serializer):
    type = serializers.CharField()
