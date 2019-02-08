# coding:utf-8
from django.utils import timezone
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
import decimal
import re
import datetime

from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.funtions import timetuple, decimal2string
from MyAbstract.serializers import MyModelSerializer
from common.models import MyUser, Shop, ShopPhoto, ShopActivity, ShopDiscount, ShopWallet, ShopBusinessLicence, \
    ShopLicence, ShopRequire, ShopCombo, ShopComboGoods, TradeDiscountProfile, TradeTicketProfile, SmsVerCode, \
    ShopMemberCard, CardDiscount, ShopMember, RandomNickImage, ShopMemberRecharge, ShopMemberService, \
    ShopMemberRechargeTime, ShopMemberRechargeCount, ShopSpoke, FriendGroup, ShopSpokeGroup, TradeMemberProfile, \
    TradeShop, TradePay, ShopSpokeRequest, ShopSpokeRequestHistory, CashRecord, ShopPayZSProfile, ShopFlyer, \
    ShopFlyerDiscountProfile, ShopFlyerReduceProfile, ShopFlyerExperienceProfile, ShopFlyerExperienceGoods, \
    Flyer2Shop, TradeExperienceProfile, TradeRecord, ShopMemberDelSnap, ShopManagerShip, MyUserSellerSettingProfile
from common.function import register_profile
from common.serializers import ShopLicenceSerializer, ShopPhotoSerializer, ShopBusinessLicenceSerializer, \
    ShopComboGoodsSerializer, CardDiscountSerializer, AbstractCashRecordListSerializer, AbstractCashRecordSerializer
from APNS import apns_push


class ShopDiscountSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopDiscount
        fields = ('discount', 'is_valid', 'full_price', 'reduce_price', 'type')

class ShopListAppSerializer(serializers.ModelSerializer):
    ico = serializers.ImageField(source='ico_thumbnail')
    state = serializers.CharField(source='get_state_display')
    is_seller = serializers.SerializerMethodField()

    def get_is_seller(self, obj):
        return obj.is_seller

    class Meta:
        model = Shop
        fields = ('id', 'name', 'ico', 'address', 'state', 'is_seller')

class ShopSerializer(MyModelSerializer):
    ico = CompressBase64ImageField()
    face = CompressBase64ImageField()
    business_licence = ShopBusinessLicenceSerializer()
    licences = ShopLicenceSerializer(many=True)
    activity = serializers.CharField()
    discount = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField(source='get_state_display')
    is_seller = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()
    have_pay_pw = serializers.SerializerMethodField()

    def get_is_seller(self, obj):
        return obj.is_seller

    def get_is_manager(self, obj):
        return obj.is_manager

    def get_have_pay_pw(self, obj):
        return obj.have_pay_pw

    class Meta:
        model = Shop
        fields = ('id', 'name', 'address', 'latitude', 'longitude', 'ico', 'face', 'level', 'activity',
                  'discount', 'business_licence', 'phone', 'type', 'seller', 'managers', 'describe', 'licences',
                  'open_time', 'close_time', 'convenience', 'state', 'is_seller', 'is_manager', 'have_pay_pw')
        read_only_fields = ('state', 'is_seller', 'is_manager', 'have_pay_pw', 'level', 'activity', 'discount',)
        custom_fields = ('is_seller', 'is_manager', 'have_pay_pw')

class ShopRequireSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopRequire
        fields = ('require1', 'require2', 'require3')

class ShopRequestJudgeSerializer(serializers.Serializer):
    judge = serializers.BooleanField()

class WalletLooseChangeSerializer(serializers.ModelSerializer):
    loose_change = serializers.SerializerMethodField()

    def get_loose_change(self, obj):
        return decimal2string(obj.loose_change())

    class Meta:
        model = ShopWallet
        fields = ('loose_change',)
        read_only_fields = ('loose_change',)

class WalletBonusSerializer(MyModelSerializer):
    bonus_pool = serializers.SerializerMethodField()
    warning_line = serializers.SerializerMethodField()
    has_card = serializers.SerializerMethodField()
    attention = serializers.SerializerMethodField()

    def get_bonus_pool(self, obj):
        return decimal2string(obj.bonus_pool)

    def get_warning_line(self, obj):
        return decimal2string(obj.bonus_warning)

    def get_has_card(self, obj):
        return hasattr(obj, 'bankcard')

    def get_attention(self, obj):
        return obj.attention

    class Meta:
        model = ShopWallet
        fields = ('bonus_pool', 'warning_line', 'has_card', 'attention')
        read_only_fields = ('bonus_pool', 'warning_line', 'has_card', 'attention')

class TradeFilterSerializer(serializers.Serializer):
    begin_time = serializers.DateField()
    end_time = serializers.DateField()
    pay_type = serializers.ChoiceField(choices=['wx', 'ali'], required=False)

    def validate_end_time(self, value):
        value += datetime.timedelta(days=1)

        return value

class TradeDiscountSerializer(MyModelSerializer):
    trade_number = serializers.CharField(source='trade.trade_number')
    total_fee = serializers.CharField(source='trade.total_fee')
    discount = serializers.CharField(source='trade.discount')
    buyer_ico = serializers.ImageField(source='trade.buyer.ico_thumbnail')
    buyer_name = serializers.CharField(source='trade.buyer.nick_name')

    def to_representation(self, instance):
        representation = super(TradeDiscountSerializer, self).to_representation(instance)

        representation['trade_time'] = timetuple(instance.trade.trade_time)
        representation['pay_platform_expend'] = decimal2string(instance.pay_platform_expend if instance.pay_platform_expend else 0 + instance.owner_earning if instance.owner_earning else 0)
        representation['pay_type'] = ','.join(instance.trade.pay_type(True))

        request = self.context.get('request', None)

        if instance.ticket:
            representation['ticket_type'] = instance.ticket.flyer.get_type_display()
            representation['spoker_type'] = 'shop'
            url = instance.ticket.shop.ico_thumbnail.url
            representation['spoker_ico'] = request.build_absolute_uri(url) if request else url
            representation['spoker_name'] = instance.ticket.shop.name
            representation['brokerage'] = instance.ticket.flyer.bonus
        else:
            representation['spoker_type'] = 'spoker'
            url = instance.trade.spokesman.ico_thumbnail.url
            representation['spoker_ico'] = request.build_absolute_uri(url) if request else url
            representation['spoker_name'] = instance.trade.spokesman.nick_name
            representation['brokerage'] = instance.brokerage

            for item in instance.trade.tradepay_set.all():
                if  'member' == item.pay_type:
                    representation['after'] = decimal2string(item.remain) if item.remain else '0'
                    break

        return representation

    class Meta:
        model = TradeDiscountProfile
        fields = ('activity', 'trade_price', 'brokerage', 'status', 'trade_number', 'discount', 'buyer_ico', 'buyer_name', 'total_fee')

class TradeTicketSerializer(MyModelSerializer):
    total_fee = serializers.CharField(source='combo.activity_price')
    discount = serializers.CharField(source='trade.discount')
    combo_ico = serializers.ImageField(source='combo.ico_thumbnail')
    combo_name = serializers.CharField(source='combo.name')
    spoker_ico = serializers.ImageField(source='trade.spokesman.ico_thumbnail')
    spoker_name = serializers.CharField(source='trade.spokesman.nick_name')
    buyer_ico = serializers.ImageField(source='trade.buyer.ico_thumbnail')
    buyer_name = serializers.CharField(source='trade.buyer.nick_name')

    def to_representation(self, instance):
        representation = super(TradeTicketSerializer, self).to_representation(instance)

        representation['trade_time'] = timetuple(instance.trade.trade_time)
        representation['pay_platform_expend'] = decimal2string(instance.pay_platform_expend if instance.pay_platform_expend else 0 + instance.owner_earning if instance.owner_earning else 0)
        representation['pay_type'] = ','.join(instance.trade.pay_type(True))

        return representation

    class Meta:
        model = TradeTicketProfile
        fields = ('ticket_number', 'trade_price', 'brokerage', 'trade_price', 'discount',
                  'combo_ico', 'combo_name', 'spoker_ico', 'spoker_name', 'buyer_ico', 'buyer_name', 'total_fee')

class TradeMemberSerializer(MyModelSerializer):
    trade_number = serializers.CharField(source='trade.trade_number')
    trade_price = serializers.CharField(source='trade.trade_price')

    def to_representation(self, instance):
        representation = super(TradeMemberSerializer, self).to_representation(instance)

        try:
            member = ShopMember.objects.get(shop=instance.trade.shop, user=instance.trade.buyer)
        except ShopMember.DoesNotExist:
            member = ShopMemberDelSnap.objects.filter(shop=instance.trade.shop, user=instance.trade.buyer).order_by('-id')[0]

        representation['member_id'] = member.id
        representation['name'] = member.name
        representation['trade_time'] = timetuple(instance.trade.trade_time)
        representation['pay_type'] = ','.join(instance.trade.pay_type(True))

        #充值
        representation['gift'] = decimal2string(instance.recharge.gift)
        representation['after'] = decimal2string(instance.recharge.after)

        return representation

    class Meta:
        model = TradeMemberProfile
        fields = ('trade_price', 'trade_number')

class TradeExperienceSerializer(MyModelSerializer):
    ticket_number = serializers.CharField(source='ticket.ticket_number')
    ticket_type = serializers.CharField(source='ticket.flyer.get_type_display')
    buyer_ico = serializers.ImageField(source='trade.buyer.ico_thumbnail')
    buyer_name = serializers.CharField(source='trade.buyer.nick_name')
    spoker_ico = serializers.ImageField(source='ticket.shop.ico_thumbnail')
    spoker_name = serializers.CharField(source='ticket.shop.name')
    brokerage = serializers.SerializerMethodField()
    trade_time = serializers.SerializerMethodField()

    def get_brokerage(self, obj):
        return decimal2string(obj.ticket.flyer.bonus)

    def get_trade_time(self, obj):
        return timetuple(obj.trade.trade_time)

    class Meta:
        model = TradeExperienceProfile
        fields = ('ticket_number', 'ticket_type', 'buyer_ico', 'buyer_name', 'spoker_ico', 'spoker_name',
                  'trade_time', 'brokerage')

class TradeShopSerializer(MyModelSerializer):
    def to_representation(self, instance):
        representation = super(TradeShopSerializer, self).to_representation(instance)

        representation['trade_time'] = timetuple(instance.trade_time)
        representation['pay_type'] = instance.pay.get_pay_type_display()
        representation['trade_price'] = decimal2string(instance.trade_price)

        return representation

    class Meta:
        model = TradeShop
        fields = ('trade_number', )

class FriendSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    ico = serializers.CharField()
    work = serializers.CharField(required=False)

class BaseBillAppSerializer(serializers.Serializer):
    sale_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_day = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_day_wx = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_day_ali = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_yesterday = serializers.DecimalField(max_digits=10, decimal_places=2)

    def my_init(self, bill):
        self.sale_month, self.sale_day, self.sale_day_wx, self.sale_day_ali, self.sale_yesterday = bill


class ShopComboSerializer(serializers.ModelSerializer):
    ico = CompressBase64ImageField()
    goods = ShopComboGoodsSerializer(many=True, required=False)

    class Meta:
        model = ShopCombo
        fields = ('id', 'name', 'ico', 'original_price', 'activity_price',
                  'valid_period_end',  'use_time', 'precautions', 'tips', 'goods', 'festival')
        read_only_fields = ('id',)

    def create(self, validated_data):
        goods = None
        if 'goods' in validated_data:
            goods = validated_data.pop('goods')
        combo = serializers.ModelSerializer.create(self, validated_data)
        if goods:
            ShopComboGoods.objects.bulk_create([ShopComboGoods(combo=combo, **item) for item in goods])

        return combo

    def update(self, instance, validated_data):
        goods = None
        if 'goods' in validated_data:
            goods = validated_data.pop('goods')
        combo = serializers.ModelSerializer.update(self, instance=instance, validated_data=validated_data)

        if goods:
            tmp1 = set()
            tmp_update = set()
            tmp_delete = set()

            for item in goods:
                if 'id' in item.keys():
                    tmp1.add(item['id'])

            tmp = ShopComboGoods.objects.filter(pk__in=tmp1, combo=combo)
            for item in tmp:
                tmp_update.add(item.id)

            tmp = ShopComboGoods.objects.filter(combo=combo)
            for item in tmp:
                if item.id not in tmp_update:
                    tmp_delete.add(item.id)

            for item in goods:
                if 'id' in item.keys() and item['id'] in tmp_update:
                    #update
                    ShopComboGoods.objects.filter(pk=item['id'], combo=combo).update(**item)
                else:
                    #create
                    ShopComboGoods.objects.create(combo=combo, **item)

            #delete
            ShopComboGoods.objects.filter(pk__in=tmp_delete).delete()

        return combo

class ConfirmTicketSerializer(serializers.Serializer):
    tickets = serializers.ListField(child=serializers.CharField())

class BindBankcardSerializer(serializers.Serializer):
    card_name = serializers.CharField()
    master_name = serializers.CharField()
    phone = serializers.CharField()
    verification_code = serializers.CharField()

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

class SetMinCashSerializer(serializers.Serializer):
    min_cash = serializers.IntegerField()

class CardDiscountAppSerializer(serializers.ModelSerializer):

    class Meta:
        model = CardDiscount
        fields = ('type', 'discount', 'full_price', 'reduce_price')

class ShopMemberRechargeSerializer(serializers.ModelSerializer):
    member_card_name = serializers.SerializerMethodField()

    def get_member_card_name(self, obj):
        return obj.member_card.name

    class Meta:
        model = ShopMemberRecharge
        fields = ('id', 'member_card', 'member_card_name', 'recharge', 'gift')
        read_only_fields = ('id', )

class ShopMemberServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopMemberService
        fields = ('id', 'name')
        read_only_fields = ('id',)

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

class ShopMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField()
    phone = serializers.CharField()
    member_card = serializers.IntegerField(write_only=True, required=False)
    card = serializers.CharField(read_only=True)
    ico = serializers.ImageField(read_only=True)
    loose_change = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    recharge_id = serializers.IntegerField(write_only=True, required=False)
    remark = serializers.CharField(required=False)

    def validate(self, attrs):
        p2 = re.compile('^1\d{10}$')
        if not p2.match(attrs['phone']):
            raise serializers.ValidationError("phone number error")

        return attrs

    def create(self, validated_data):
        request = validated_data.pop('request')
        phone = validated_data['phone']
        if 'id' in validated_data.keys():
            validated_data.pop('id')

        try:
            user = MyUser.objects.get(phone_number=phone)
        except MyUser.DoesNotExist:
            temp = RandomNickImage.objects.all().order_by('?')[0]
            user = MyUser(username=phone, nick_name=temp.nick, ico=temp.image)
            user.set_unusable_password()
            user.save()
            register_profile(request, user)

        validated_data['user'] = user

        if 'member_card' in validated_data.keys():
            validated_data['member_card'] = ShopMemberCard.objects.get(pk=validated_data['member_card'])
        elif 'member_card' not in validated_data.keys() and 'recharge_id' in validated_data.keys():
            shop_member_recharge = ShopMemberRecharge.objects.get(pk=validated_data['recharge_id'])
            validated_data['member_card'] = shop_member_recharge.member_card
            validated_data.pop('recharge_id')
            if 'loose_change' not in validated_data.keys():
                validated_data['loose_change'] = shop_member_recharge.recharge + shop_member_recharge.gift
        else:
            raise ValidationDict211Error('member_card error')

        member = ShopMember.objects.create(**validated_data)
        shop_id = validated_data['shop_id']
        # existing spoker are coverded into members
        if ShopSpoke.objects.filter(shop_id=shop_id, spokesman=user).exists():
            ShopSpoke.objects.filter(shop_id=shop_id, spokesman=user).update(spokesman=None, member=member, type='member')
        else:
            try:
                # todo
                obj = ShopSpokeRequest.objects.get(resume__user=user, shop_id=shop_id)
                ShopSpokeRequestHistory.objects.create(shop=obj.shop, spokesman=obj.resume.user, request_time=obj.request_time, result=False)
                obj.delete()
            except:
                pass

            ShopSpoke.objects.create(shop_id=shop_id, member=member, type='member')
            group = FriendGroup.objects.get(user=user, type=3)
            discount = member.member_card.discount.discount if hasattr(member.member_card, 'discount') else 100
            ShopSpokeGroup.objects.create(shop_id=shop_id, group=group, discount=(0.5 * discount + 50))

        apns_push.handle_seller_member_create(user, member.shop, member.user.nick_name,
                                              member.member_card.name)

        return member

class ShopMemberBatchSerializer(serializers.Serializer):
    members = ShopMemberSerializer(many=True)

    def create(self, validated_data):
        request = validated_data.pop('request')
        shop_id = validated_data.pop('shop_id')

        failed = []

        for item in validated_data['members']:
            serializer = ShopMemberSerializer(item)

            item['request'] = request
            item['shop_id'] = shop_id
            phone = item['phone']
            if not ShopMember.objects.filter(shop_id=shop_id, user__phone_number=phone).exists():
                serializer.create(item)
            else:
                if 'id' in item.keys():
                    temp = {'id':item['id'], 'reason':'已是会员'}
                    failed.append(temp)

        return failed

class TradeMemberRechageSerializer(serializers.Serializer):
    recharge_id = serializers.IntegerField()

class TradeMemberRechageInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    gift = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)

class TradeMemberRechageTimeInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_id = serializers.IntegerField()
    month = serializers.IntegerField()

class TradeMemberRechageCountInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_id = serializers.IntegerField()
    count = serializers.IntegerField()

class TradeMemberConsumeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class TradeMemberConsumeTimeSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    month = serializers.IntegerField()

class TradeMemberConsumeCountSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    count = serializers.IntegerField()

class MemberRechargeHistoryAppSerializer(serializers.ModelSerializer):
    trade_number = serializers.CharField(source='trade.trade_number')
    trade_time = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    discribe = serializers.SerializerMethodField()
    after = serializers.SerializerMethodField()

    def get_trade_time(self, obj):
        return timetuple(obj.trade.trade_time)

    def get_name(self, obj):
        try:
            return ShopMember.objects.get(shop=obj.trade.shop, user=obj.trade.buyer).name
        except ShopMember.DoesNotExist:
            return ShopMemberDelSnap.objects.filter(shop=obj.trade.shop, user=obj.trade.buyer).order_by('-id')[0].name

    def get_discribe(self, obj):
        # Todo have three choice
        if obj.recharge:
            return '充{0}赠送{1}元'.format(obj.recharge.recharge, obj.recharge.gift) if obj.recharge.gift > 0 \
                else '充{0}元'.format(obj.recharge.recharge)

    def get_after(self, obj):
        # Todo have three choice
        if obj.recharge:
            return decimal2string(obj.recharge.after)

    class Meta:
        model = TradeMemberProfile
        fields = ('trade_number', 'trade_time', 'name', 'discribe', 'after')

class MemberRechargeHistorySerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    trade_time = serializers.SerializerMethodField()
    recharge = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    card_name = serializers.SerializerMethodField()
    gift = serializers.SerializerMethodField()
    after = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.trade.id

    def get_trade_time(self, obj):
        return timetuple(obj.trade.trade_time)

    def get_recharge(self, obj):
        return decimal2string(obj.trade_price)

    def get_amount(self, obj):
        return decimal2string(obj.trade_price + obj.discount_reduce)

    def get_member_name(self, obj):
        try:
            return ShopMember.objects.get(shop=obj.trade.shop, user=obj.trade.buyer).name
        except ShopMember.DoesNotExist:
            return ShopMemberDelSnap.objects.filter(shop=obj.trade.shop, user=obj.trade.buyer).order_by('-id')[0].name

    def get_card_name(self, obj):
        # Todo have three choice
        try:
            return obj.trade.tradepay_set.all()[0].card_name
        except:
            return None

    def get_gift(self, obj):
        # Todo have three choice
        if obj.recharge:
            return '赠送￥{0}元'.format(obj.recharge.gift) if obj.recharge.gift > 0 else None

    def get_after(self, obj):
        # Todo have three choice
        if obj.recharge:
            return obj.recharge.after

    class Meta:
        model = TradeMemberProfile
        fields = ('id', 'recharge', 'trade_time', 'amount', 'member_name', 'card_name', 'gift', 'after')

class MemberConsumeHistoryAppSerializer(serializers.ModelSerializer):
    trade_number = serializers.CharField(source='trade.trade_number')
    trade_time = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    def get_trade_time(self, obj):
        return timetuple(obj.trade.trade_time)

    def get_amount(self, obj):
        return decimal2string(obj.trade_price)

    def get_name(self, obj):
        try:
            return ShopMember.objects.get(shop=obj.trade.shop, user=obj.trade.buyer).name
        except ShopMember.DoesNotExist:
            return ShopMemberDelSnap.objects.filter(shop=obj.trade.shop, user=obj.trade.buyer).order_by('-id')[0].name

    class Meta:
        model = TradePay
        fields = ('trade_number', 'trade_time', 'name', 'amount', 'remain')

class MemberConsumeHistorySerializer(serializers.ModelSerializer):
    trade_time = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    is_myself = serializers.SerializerMethodField()

    def get_trade_time(self, obj):
        return timetuple(obj.trade.trade_time)

    def get_amount(self, obj):
        return decimal2string(obj.trade_price)

    def get_member_name(self, obj):
        try:
            return ShopMember.objects.get(shop=obj.trade.shop, user=obj.trade.buyer).name
        except ShopMember.DoesNotExist:
            return ShopMemberDelSnap.objects.filter(shop=obj.trade.shop, user=obj.trade.buyer).order_by('-id')[0].name

    def get_is_myself(self, obj):
        return True

    class Meta:
        model = TradePay
        fields = ('id', 'card_name', 'trade_time', 'amount', 'member_name', 'is_myself', 'remain')

class TimeFilterSerializer(serializers.Serializer):
    begin_time = serializers.DateField(required=False)
    end_time = serializers.DateField(required=False)

class CashRecordListSerializer(AbstractCashRecordListSerializer):
    class Meta:
        model = CashRecord
        fields = ('id', 'request_time', 'cash', 'status')

class CashRecordSerializer(AbstractCashRecordSerializer):
    class Meta:
        model = CashRecord
        fields = ('id', 'cash', 'charge', 'status', 'trace',
                  'request_bank_name', 'request_acc_no')

class BounsPoolSerializer(serializers.Serializer):
    total_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    pay_type = serializers.IntegerField()

class ShopFlyerSerializer(MyModelSerializer):
    img = CompressBase64ImageField()
    bonus_type = serializers.SerializerMethodField()
    describe = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()
    describe2 = serializers.SerializerMethodField()

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'img', 'bonus', 'valid_period_end', 'describe', 'bonus_type', 'combo_name', 'describe2')
        custom_fields = ('bonus_type', 'combo_name', 'describe2')

    def get_bonus_type(self, obj):
        if 1 == obj.type:
            return obj.discount.bonus_type

        return None

    def get_describe(self, obj):
        if 1 == obj.type:
            return '店内消费{0}折'.format(obj.discount.discount / 10)
        elif 2 == obj.type:
            return '店内消费满{0}减{1}'.format(obj.reduce.full_price, obj.reduce.reduce_price)
        elif 3 == obj.type:
            return '原价: {0}'.format(obj.experience.original_price)

        return None

    def get_describe2(self, obj):
        if 1 == obj.type:
            return '最低消费: {0}元'.format(obj.discount.full_price)

        return None

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

class ShopFlyerNearbySerializer(ShopFlyerSerializer):
    shop_name = serializers.CharField(source='shop.name')
    phone = serializers.CharField(source='shop.phone')
    bonus_type = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    league = serializers.SerializerMethodField()
    league_id =serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    describe2 = serializers.SerializerMethodField()

    def get_status(self, obj):
        if obj.status == 'limit':
            status = 'limit'
        elif Flyer2Shop.objects.filter(flyer=obj).count() >= 20:
            status = 'full'
        else:
            status = 'normal'

        return status

    def get_describe2(self, obj):
        if 1 == obj.type:
            return '最低消费: {0}元'.format(obj.discount.full_price)

        return None

    class Meta:
        model = ShopFlyer
        fields = ('id', 'shop_id', 'type', 'img', 'bonus', 'valid_period_end', 'describe', 'combo_name',
                  'shop_name', 'phone', 'distance', 'league', 'league_id', 'status', 'describe2', 'bonus_type')
        custom_fields = ('combo_name', 'league_id', 'describe2', 'bonus_type')

    def get_bonus_type(self, obj):
        if 1 == obj.type:
            return obj.discount.bonus_type

        return None

    def get_distance(self, obj):
        return int(obj.distance)

    def get_league(self, obj):
        return obj.league

    def get_league_id(self, obj):
        return obj.league_id if hasattr(obj, 'league_id') else None

class ShopFlyerInnerSerializer(MyModelSerializer):
    img = CompressBase64ImageField()
    type = serializers.IntegerField(required=False)

    class Meta:
        model = ShopFlyer
        fields = ('id', 'img', 'bonus', 'valid_period_end',
                  'day_begin', 'day_end', 'festival', 'precautions', 'tips', 'type')

class ShopFlyerProfileSerializer(serializers.Serializer):
    flyer = ShopFlyerInnerSerializer(required=False)
    bonus_type = serializers.IntegerField(required=False)
    discount = serializers.IntegerField(required=False)
    full_price = serializers.IntegerField(required=False)
    reduce_price = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    original_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    goods = ShopComboGoodsSerializer(many=True, required=False)

    def validate(self, attrs):
        if 'bonus_type' in attrs.keys() and attrs['bonus_type'] not in (1, 2):
            raise ValidationDict211Error('bonus_type error')

        return attrs

class AbstractShopFlyerProfileSerializer(serializers.ModelSerializer):
    flyer = ShopFlyerInnerSerializer()
    shop_name = serializers.CharField(source='flyer.shop.name', read_only=True)
    shop_address = serializers.CharField(source='flyer.shop.address', read_only=True)
    shop_phone = serializers.CharField(source='flyer.shop.phone', read_only=True)
    describe = serializers.SerializerMethodField()

    class Meta:
        fields = ('flyer', 'shop_name', 'shop_address', 'shop_phone', 'describe')

    def get_describe(self, obj):
        if 1 == obj.flyer.type:
            return '店内消费{0}折'.format(obj.discount / 10)
        elif 2 == obj.flyer.type:
            return '店内消费满{0}减{1}'.format(obj.full_price, obj.reduce_price)
        elif 3 == obj.flyer.type:
            return '原价: {0}'.format(obj.original_price)

        return None

class ShopFlyerDiscountSerializer(AbstractShopFlyerProfileSerializer):
    class Meta:
        model = ShopFlyerDiscountProfile
        fields = tuple(set(['bonus_type', 'discount', 'full_price']) | set(AbstractShopFlyerProfileSerializer.Meta.fields))

    def validate(self, attrs):
        if attrs['bonus_type'] not in (1, 2):
            raise ValidationDict211Error('bonus_type error')
        elif 2 == attrs['bonus_type']:
            if attrs['flyer']['bonus'] > 100:
                raise ValidationDict211Error('bonus error')

            attrs['flyer']['bonus'] = int(attrs['flyer']['bonus'])

        return attrs

    def create(self, validated_data):
        shop_id = validated_data.pop('shop_id')
        flyer = validated_data.pop('flyer')
        if ShopFlyer.objects.filter(shop_id=shop_id, status='online').exists():
            raise serializers.ValidationError('has one flyer')
        flyer = ShopFlyer.objects.create(shop_id=shop_id, type=1, **flyer)
        profile = self.Meta.model.objects.create(flyer=flyer, **validated_data)

        return profile

class ShopFlyerReduceSerializer(AbstractShopFlyerProfileSerializer):
    class Meta:
        model = ShopFlyerReduceProfile
        fields = tuple(set(['full_price', 'reduce_price']) | set(AbstractShopFlyerProfileSerializer.Meta.fields))

    def create(self, validated_data):
        shop_id = validated_data.pop('shop_id')
        flyer = validated_data.pop('flyer')
        if ShopFlyer.objects.filter(shop_id=shop_id, status='online').exists():
            raise serializers.ValidationError('has one flyer')
        flyer = ShopFlyer.objects.create(shop_id=shop_id, type=2, **flyer)
        profile = self.Meta.model.objects.create(flyer=flyer, **validated_data)

        return profile

class ShopFlyerExperienceGoodsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ShopFlyerExperienceGoods
        fields = ('id', 'name', 'price', 'num', 'unit')
        read_only_fields = ('id', )

class ShopFlyerExperienceSerializer(AbstractShopFlyerProfileSerializer):
    goods = ShopComboGoodsSerializer(many=True)

    class Meta:
        model = ShopFlyerExperienceProfile
        fields = tuple(set(['name', 'original_price', 'goods']) | set(AbstractShopFlyerProfileSerializer.Meta.fields))

    def create(self, validated_data):
        shop_id = validated_data.pop('shop_id')
        goods = validated_data.pop('goods')
        flyer = validated_data.pop('flyer')
        if ShopFlyer.objects.filter(shop_id=shop_id, status='online').exists():
            raise serializers.ValidationError('has one flyer')
        flyer = ShopFlyer.objects.create(shop_id=shop_id, type=3, **flyer)
        profile = self.Meta.model.objects.create(flyer=flyer, **validated_data)
        ShopFlyerExperienceGoods.objects.bulk_create(
            [ShopFlyerExperienceGoods(combo=profile, **item) for item in goods])

        return profile

class Flyer2ShopMineSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='shop.name')
    ico = serializers.ImageField(source='shop.ico')
    distance = serializers.SerializerMethodField()
    phone = serializers.CharField(source='shop.phone')
    bonus_type = serializers.SerializerMethodField()
    bonus = serializers.SerializerMethodField()


    def get_distance(self, obj):
        return int(obj.distance)

    def get_bonus_type(self, obj):
        flyer = obj.flyer
        return 2 if flyer.type == 1 and flyer.discount.bonus_type == 2 else 1

    def get_bonus(self, obj):
        return decimal2string(obj.flyer.bonus)

    class Meta:
        model = Flyer2Shop
        fields = ('id', 'name', 'ico', 'distance', 'phone', 'bonus_type', 'bonus', 'count', 'flyer_id')

class Flyer2ShopOhterSerializer(MyModelSerializer):
    img = CompressBase64ImageField()
    describe = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()
    bonus_type = serializers.SerializerMethodField()

    shop_name = serializers.CharField(source='shop.name')
    phone = serializers.CharField(source='shop.phone')
    distance = serializers.SerializerMethodField()

    id = serializers.SerializerMethodField()
    flyer_id = serializers.IntegerField(source='id')
    status = serializers.SerializerMethodField()
    describe2 = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.temp

    def get_describe(self, obj):
        if 1 == obj.type:
            return '店内消费{0}折'.format(obj.discount.discount / 10)
        elif 2 == obj.type:
            return '店内消费满{0}减{1}'.format(obj.reduce.full_price, obj.reduce.reduce_price)
        elif 3 == obj.type:
            return '原价: {0}'.format(obj.experience.original_price)

        return None

    def get_describe2(self, obj):
        if 1 == obj.type:
            return '最低消费: {0}元'.format(obj.discount.full_price)

        return None

    def get_bonus_type(self, obj):
        if 1 == obj.type:
            return obj.discount.bonus_type

        return None

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

    def get_distance(self, obj):
        return int(obj.distance)

    def get_status(self, obj):
        if obj.status == 'limit':
            status = 'limit'
        else:
            status = 'normal'

        return status

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'img', 'bonus', 'valid_period_end', 'describe', 'combo_name',
                  'shop_name', 'phone', 'distance', 'shop_id', 'flyer_id', 'status', 'describe2', 'bonus_type')
        custom_fields = ('combo_name', 'describe2', 'bonus_type')

class FlyerTradeOtherSerializer(serializers.Serializer):
    buyer_name = serializers.CharField()
    buyer_ico = serializers.CharField()
    shop_name = serializers.CharField()
    shop_ico = serializers.CharField()
    time = serializers.IntegerField()
    trade_type = serializers.CharField()
    type = serializers.IntegerField()
    bonus = serializers.CharField()
    bonus_type = serializers.SerializerMethodField()

    def get_bonus_type(self, obj):
        if 1 == obj.type:
            return obj.discount.bonus_type

        return None

class FlyerTradeMineSerializer(FlyerTradeOtherSerializer):
    number = serializers.CharField()
    trade_price = serializers.CharField()

class Interface1RequestSerializer(serializers.Serializer):
    type = serializers.CharField()

class Interface1ResponseSerializer(serializers.Serializer):
    version = serializers.CharField()
    no_disturb = serializers.BooleanField()
    apns_voice = serializers.BooleanField()

class ShopHomeSerializer(serializers.ModelSerializer):
    ico = serializers.ImageField(source='ico_thumbnail')
    is_seller = serializers.SerializerMethodField()
    is_manager = serializers.SerializerMethodField()

    def get_is_seller(self, obj):
        return obj.is_seller

    def get_is_manager(self, obj):
        return obj.is_manager

    class Meta:
        model = Shop
        fields = ('id', 'name', 'ico', 'is_seller', 'is_manager')
        read_only_fields = ('ico', 'face',)

class HomeAppSerializer(serializers.Serializer):
    shop = ShopHomeSerializer()
    bill = BaseBillAppSerializer()

    def my_init(self, shop, bill):
        self.shop = shop
        self.bill = bill

class ShopMemberListAppSerializer(serializers.ModelSerializer):
    ico = serializers.ImageField(source='user.ico_thumbnail')
    card = serializers.CharField(source='member_card.name')

    class Meta:
        model = ShopMember
        fields = ('id', 'name', 'ico', 'card')

class ShopMemberCardListSerializer(serializers.ModelSerializer):
    shop_name = serializers.CharField(source='shop.name')

    class Meta:
        model = ShopMemberCard
        fields = ('id', 'name', 'image', 'shop_name')

class ShopRequireAppSerializer(serializers.ModelSerializer):
    request_count = serializers.SerializerMethodField()
    max_count = serializers.IntegerField(source='shop.max_spoke')
    current_count = serializers.IntegerField(source='shop.spoke_count')

    def get_request_count(self, obj):
        return obj.shop.shopspokerequest_set.count()

    class Meta:
        model = ShopRequire
        fields = ('require1', 'require2', 'require3', 'request_count', 'max_count', 'current_count')

class ShopSpokerListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ico = serializers.CharField()
    name = serializers.CharField()
    is_seller = serializers.BooleanField(required=False)
    is_manager = serializers.BooleanField()
    count = serializers.IntegerField()
    sale = serializers.CharField()

class ShopSpokerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ico = serializers.CharField()
    name = serializers.CharField()
    phone = serializers.CharField()
    begin_time = serializers.IntegerField()
    is_seller = serializers.BooleanField(required=False)
    is_manager = serializers.BooleanField(required=False)
    count = serializers.IntegerField()
    sale = serializers.CharField()
    brokerage = serializers.CharField()

class ShopSpokeRequestListSerializer(MyModelSerializer):
    ico = serializers.ImageField(source='ico_thumbnail')
    name = serializers.CharField(source='nick_name')
    phone = serializers.CharField(source='phone_number')

    class Meta:
        model = MyUser
        fields = ('id', 'ico', 'name', 'phone')

class ShopSpokesRequestAppSerializer(MyModelSerializer):
    ico = serializers.ImageField(source='ico_thumbnail')
    name = serializers.CharField(source='nick_name')
    phone = serializers.CharField(source='phone_number')
    real_name = serializers.CharField(source='nationalid.real_name', required=False)
    work = serializers.CharField(source='resume.work', required=False)
    resume = serializers.CharField(source='resume.resume')
    request_time = serializers.SerializerMethodField()

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    class Meta:
        model = MyUser
        fields = ('id', 'ico', 'name', 'phone', 'female', 'birthday', 'real_name', 'work', 'resume', 'request_time')
        custom_fields = ('female', 'birthday', 'real_name', 'work')

class ShopSpokerResumeSerializer(MyModelSerializer):
    ico = serializers.ImageField(source='ico_thumbnail')
    name = serializers.CharField(source='nick_name')
    phone = serializers.CharField(source='phone_number')
    real_name = serializers.CharField(source='nationalid.real_name', required=False)
    work = serializers.CharField(source='resume.work', required=False)
    resume = serializers.CharField(source='resume.resume')

    class Meta:
        model = MyUser
        fields = ('id', 'ico', 'name', 'phone', 'female', 'birthday', 'real_name', 'work', 'resume')
        custom_fields = ('birthday', 'real_name', 'work')

class ShopMemberCardSerializer(MyModelSerializer):
    class ShopMemberRechargeInnerSerializer(MyModelSerializer):

        class Meta:
            model = ShopMemberRecharge
            fields = ('recharge', 'gift')

    image = Base64ImageField()
    discount = CardDiscountAppSerializer(required=False)
    recharge = ShopMemberRechargeInnerSerializer(many=True, required=False)

    def create(self, validated_data):
        if 'discount' in validated_data:
            discount = validated_data.pop('discount')
        else:
            discount = {}
        recharge = None
        if 'recharge' in validated_data:
            recharge = validated_data.pop('recharge')

        shop_member_card = serializers.ModelSerializer.create(self, validated_data)
        CardDiscount.objects.create(member_card=shop_member_card, **discount)
        if recharge:
            ShopMemberRecharge.objects.bulk_create([ShopMemberRecharge(shop=shop_member_card.shop, member_card=shop_member_card, **item) for item in recharge])

        return shop_member_card

    def update(self, instance, validated_data):
        discount = None
        if 'discount' in validated_data.keys():
            discount = validated_data.pop('discount')

        recharge = None
        if 'recharge' in validated_data.keys():
            recharge = validated_data.pop('recharge')
        shop_member_card = serializers.ModelSerializer.update(self, instance=instance, validated_data=validated_data)
        shop_member_card.save()

        if discount:
            old_discount = shop_member_card.discount.discount if hasattr(shop_member_card, 'discount') else 100

            if hasattr(shop_member_card, 'discount'):
                CardDiscount.objects.filter(member_card=shop_member_card).update(**discount)
                member_discount = CardDiscount.objects.get(member_card=shop_member_card)
            else:
                discount['member_card'] = shop_member_card
                member_discount = CardDiscount.objects.create(**discount)

            queryset = ShopSpoke.objects.filter(shop=shop_member_card.shop, type='member')
            queryset = ShopSpokeGroup.objects.filter(shop=shop_member_card.shop, group__user__in=[item.member.user_id for item in queryset])

            for query in queryset:
                if old_discount < 100:
                    tmp = (query.member_discount - old_discount) / decimal.Decimal(100.0 - old_discount)
                    query.member_discount = 100 * tmp - tmp * member_discount.discount + member_discount.discount

                query.save(update_fields=['member_discount'])

        if recharge:
            ShopMemberRecharge.objects.filter(shop=shop_member_card.shop, member_card=shop_member_card).delete()
            ShopMemberRecharge.objects.bulk_create([ShopMemberRecharge(shop=shop_member_card.shop, member_card=shop_member_card, **item) for item in recharge])

        return shop_member_card

    class Meta:
        model = ShopMemberCard
        fields = ('id', 'name', 'image', 'discount', 'level', 'recharge')
        read_only_fields = ('id', )
        custom_fields = ('discount', 'recharge')

class ShopComboListSerializer(serializers.ModelSerializer):
    ico = CompressBase64ImageField()

    class Meta:
        model = ShopCombo
        fields = ('id', 'name', 'ico', 'original_price', 'activity_price', 'valid_period_end', 'status')

class BonusSerializer(serializers.Serializer):
    bonus = WalletBonusSerializer()
    discount = ShopDiscountSerializer()

class TradeSerializer(serializers.Serializer):
    buyer_ico = serializers.CharField()
    type = serializers.CharField()
    time = serializers.IntegerField()
    total_fee = serializers.CharField()
    number = serializers.CharField()
    remark = serializers.CharField(required=False)
    pay_type = serializers.CharField()

class TradeBonusSerializer(serializers.Serializer):
    time = serializers.IntegerField()
    type = serializers.CharField()
    buyer_ico = serializers.CharField()
    brokerage = serializers.CharField()
    number = serializers.CharField()

class WithdrawRecordSerializer(serializers.Serializer):
    time = serializers.IntegerField()
    amount = serializers.CharField()

class ShopManagerCreateSerializer(serializers.Serializer):
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
            ship = ShopManagerShip.objects.create(shop_id=validated_data['shop_id'], user=user, name=name)
        except:
            raise ValidationDict211Error('已存在管理员')

        return ship

class ShopManagerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    ico = serializers.ImageField(source='user.ico_thumbnail', read_only=True)
    phone = serializers.CharField(source='user.phone_number')
    password = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = ShopManagerShip
        fields = ('id', 'ico', 'phone', 'name', 'password')

class SettingSerializer(serializers.Serializer):
    no_disturb = serializers.BooleanField(required=False)
    apns_voice = serializers.BooleanField(required=False)

class InformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUserSellerSettingProfile
        fields = ('platform', 'version')

class FlyerFilterSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    shop_type = serializers.IntegerField(required=False)
    type = serializers.IntegerField(required=False)
