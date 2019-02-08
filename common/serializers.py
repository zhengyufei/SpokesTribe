import datetime

from io import BytesIO
import requests
from django.core.files.base import ContentFile
import uuid

from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.funtions import timetuple, decimal2string
from common.function import phonecheck, isidcard
from .models import ShopFirstType, MyUser, NationalId, SmsVerCode, ShopPhoto, ShopLicence,\
    Feedback, ShopBusinessLicence, ShopComboGoods, CardDiscount, RandomNickImage, AbstractCash, Shop
from Logger.logger import Logger
from MyAbstract.serializers import MyModelSerializer


class ComfirmSerializer(serializers.Serializer):
    comfirm = serializers.BooleanField()

class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("Username"))
    password = serializers.CharField(label=_("Password"), style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                # From Django 1.10 onwards the `authenticate` call simply
                # returns `None` for is_active=False users.
                # (Assuming the default `ModelBackend` authentication backend.)
                if not user.is_active:
                    #msg = _('User account is disabled.')
                    msg = '用户帐户被禁用.'
                    raise ValidationDict211Error(msg, code='authorization')
            else:
                #msg = _('Unable to log in with provided credentials.')
                msg = '无法登录提供凭证.'
                raise ValidationDict211Error(msg, code='authorization')
        else:
            #msg = _('Must include "username" and "password".')
            msg = '必须包括“用户名”和“密码”.'
            raise ValidationDict211Error(msg, code='authorization')

        attrs['user'] = user
        return attrs

class PureSmsVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()

    def validate(self, attrs):
        phone = attrs['phone']
        try:
            obj = SmsVerCode.objects.filter(phone=phone).order_by('-id')[0]
        except SmsVerCode.DoesNotExist:
            raise ValidationDict211Error('no sms1')

        if obj.obsolete or obj.expire_time < timezone.now():
            raise ValidationDict211Error('no sms2')

        return attrs

class RegisterUsernameVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        username = attrs['phone']

        if MyUser.objects.filter(username=username).exists():
            raise ValidationDict211Error('用户名已存在')

        return attrs

class SmsVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()

    TYPE = (
        (1, 'register'),
        (2, 'confirm'),
        (3, 'other')
    )

    type = serializers.ChoiceField(choices=TYPE)

    def validate(self, attrs):
        type = attrs['type']
        phone = attrs['phone']

        temp = phonecheck(phone)
        Logger.Log('info', 'screen sms {0}'.format(temp))
        if not temp[0]:
            raise ValidationDict211Error(temp[1], temp[2])

        has_obj = False
        try:
            obj = SmsVerCode.objects.filter(phone=phone).order_by('-id')[0]

            if not obj.obsolete:
                has_obj = True
        except:
            pass

        if type is 1 and MyUser.objects.filter(username=phone).exists():
            raise ValidationDict211Error('用户已注册')

        return attrs

    def save(self, validated_data):
        validated_data.pop('type')
        sms = SmsVerCode(**validated_data)
        sms.expire_time = timezone.now() + datetime.timedelta(minutes=5)
        sms.save()
        return sms

class ShopTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopFirstType
        fields = ('id', 'name',)

class UserNormalInfoSerializer(serializers.ModelSerializer):
    ico = CompressBase64ImageField()
    ico_thumbnail = CompressBase64ImageField(read_only=True)

    class Meta:
        model = MyUser
        fields = ('username', 'nick_name', 'female', 'birthday', 'ico', 'ico_thumbnail', 'describe', 'abode')
        read_only_fields = ('ico_thumbnail',)

class UserNationalIdSerializer(serializers.ModelSerializer):
    national_id_front = Base64ImageField()
    national_id_back = Base64ImageField()

    class Meta:
        model = NationalId
        fields = ('user_id', 'real_name', 'national_id', 'national_id_front', 'national_id_back', 'is_valid')
        read_only_fields = ('user_id', 'is_valid',)

    def validate(self, attrs):
        temp = isidcard(attrs['national_id'])

        if not temp[0]:
            raise ValidationDict211Error(temp[1])

        return attrs

class FindPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    verification_code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(max_length=20, min_length=6)
    confirm_password = serializers.CharField(max_length=20, min_length=6, write_only=True)

    def validate(self, attrs):
        try:
            obj = SmsVerCode.objects.filter(phone=attrs['username']).order_by('-id')[0]
        except:
            raise ValidationDict211Error('验证码未找到.')

        code = obj.code
        expire_time = obj.expire_time

        if code !=attrs['verification_code']:
            raise ValidationDict211Error('验证码不匹配.')
        elif expire_time < timezone.now():
            raise ValidationDict211Error('验证码已过期.')

        try:
            user = MyUser.objects.get(username=attrs['username'])
        except MyUser.DoesNotExist:
            raise ValidationDict211Error('用户名不存在.')
        if not user.is_active:
            raise ValidationDict211Error('该用户被锁定.')

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致.')

        obj.obsolete = True
        obj.save(update_fields=['obsolete'])

        return attrs

    def save(self, validated_data):
        user = MyUser.objects.get(username=validated_data['username'])
        user.set_password(validated_data['new_password'])
        user.save(update_fields=['password'])

        return user

class UserCreateSerializer(serializers.ModelSerializer):
    verification_code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(max_length=20, min_length=6)
    confirm_password = serializers.CharField(max_length=20, min_length=6, write_only=True)

    class Meta:
        model = MyUser
        fields = ('username','new_password','confirm_password','verification_code',)

    def validate(self, attrs):
        try:
            obj = SmsVerCode.objects.filter(phone=attrs['username']).order_by('-id')[0]
        except:
            raise ValidationDict211Error('验证码未找到.')

        code = obj.code
        expire_time = obj.expire_time

        if code !=attrs['verification_code']:
            raise ValidationDict211Error('验证码不匹配.')
        elif expire_time < timezone.now():
            raise ValidationDict211Error('验证码已过期.')

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致.')

        obj.obsolete = True
        obj.save(update_fields=['obsolete'])

        return attrs

    def save(self, validated_data, nick, ico):
        password = validated_data['new_password']
        validated_data.pop('verification_code')
        validated_data.pop('new_password')
        validated_data.pop('confirm_password')
        validated_data['phone_number'] = validated_data['username']
        validated_data['nick_name'] = nick
        validated_data['ico'] = ico
        user = MyUser(**validated_data)
        user.set_password(password)
        user.save()

        return user

class ResetPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=20, min_length=6)
    new_password = serializers.CharField(max_length=20, min_length=6)
    confirm_password = serializers.CharField(max_length=20, min_length=6, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致.')
        attrs.pop('confirm_password')
        return attrs

    def save(self, **kwargs):
        user = kwargs['user']
        if not user.check_password(self.validated_data['old_password']):
            raise ValidationDict211Error('原密码错误.')
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])

class ShopBusinessLicenceSerializer(serializers.ModelSerializer):
    business_licence = Base64ImageField()

    class Meta:
        model = ShopBusinessLicence
        fields = ('name', 'serial_number', 'valid_date', 'business_licence')

class ShopLicenceSerializer(serializers.ModelSerializer):
    licence = Base64ImageField()

    class Meta:
        model = ShopLicence
        fields = ('id', 'name', 'serial_number', 'valid_date', 'licence', )
        read_only_fields = ('id',)

class ShopPhotoSerializer(serializers.ModelSerializer):
    photo = CompressBase64ImageField()
    photo_thumbnail = CompressBase64ImageField(read_only=True)

    width = serializers.IntegerField(source='photo.width', required=False, read_only=True)
    height = serializers.IntegerField(source='photo.height', required=False, read_only=True)

    class Meta:
        model = ShopPhoto
        fields = ('id', 'photo', 'photo_thumbnail', 'width', 'height')
        read_only_fields = ('id', 'photo_thumbnail', 'width', 'height')

class FeedbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = Feedback
        fields = ('feedback', )

class FriendConfirmSerializer(serializers.Serializer):
    friend = serializers.CharField()

class FriendAliasSerializer(serializers.Serializer):
    alias = serializers.CharField()

class FriendChangeGroupSerializer(serializers.Serializer):
    friends = serializers.ListField(child=serializers.CharField())
    type = serializers.IntegerField()

class DelIDsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())

class EmptySerializer(serializers.Serializer):
    pass

class SystemMessageSerializer(serializers.Serializer):
    message = serializers.CharField()
    time = serializers.IntegerField()

class NotifyMessageSerializer(serializers.Serializer):
    message = serializers.CharField()
    time = serializers.IntegerField()
    event = serializers.CharField()

class TradeMessageSerializer(serializers.Serializer):
    status = serializers.SerializerMethodField()

    message = serializers.CharField()
    time = serializers.IntegerField()
    trade_number = serializers.CharField(required=False)
    ticket_number = serializers.CharField(required=False)
    image = CompressBase64ImageField()
    type = serializers.CharField()#income expend refund
    trade_type = serializers.CharField()#discount ticket member
    ban_jump = serializers.BooleanField(required=False)
    record_id = serializers.IntegerField(required=False)

    def get_status(self, obj):
        return '交易信息'

class ThirdLoginSerializer(serializers.Serializer):
    unionid = serializers.CharField()
    nickname = serializers.CharField(required=False)
    img_url = serializers.URLField(required=False)

    def save(self, validated_data):
        username = uuid.uuid1().hex
        password = 'fk1235813zyf0905'

        if 'nickname' not in validated_data.keys() \
            or 'img_url' not in validated_data.keys():
            temp = RandomNickImage.objects.all().order_by('?')[0]

        # Generate file name:
        if 'nickname' in validated_data.keys():
            nick = validated_data['nickname']
        else:
            nick = temp.nick

        if 'img_url' in validated_data.keys():
            response = requests.get(validated_data['img_url'])
            decoded_file = BytesIO(response.content).getbuffer()
            complete_file_name = str(uuid.uuid4())[:12] + "." + 'jpg'
            image = ContentFile(decoded_file, complete_file_name)
        else:
            image = temp.image

        user = MyUser(username=username, nick_name=nick, ico=image)
        user.set_password(password)
        user.save()

        return user

class ThirdBindSerializer(serializers.Serializer):
    unionid = serializers.CharField()
    phone = serializers.CharField()
    verification_code = serializers.CharField(write_only=True)

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

        return attrs

class ThirdBind2Serializer(serializers.Serializer):
    phone = serializers.CharField()
    verification_code = serializers.CharField(write_only=True)

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

        return attrs

class ThirdBind3Serializer(serializers.Serializer):
    unionid = serializers.CharField()

class ThirdRegisterSerializer(serializers.Serializer):
    unionid = serializers.CharField()
    phone = serializers.CharField()
    verification_code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(max_length=20, min_length=6)
    confirm_password = serializers.CharField(max_length=20, min_length=6, write_only=True)
    nickname = serializers.CharField()
    img_url = serializers.URLField()

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

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致.')

        obj.obsolete = True
        obj.save(update_fields=['obsolete'])

        return attrs

    def save(self, validated_data):
        password = validated_data['new_password']
        response = requests.get(validated_data['img_url'])
        decoded_file = BytesIO(response.content).getbuffer()
        # Generate file name:
        complete_file_name = str(uuid.uuid4())[:12] + "." + 'jpg'

        user = MyUser(username=validated_data['phone'], nick_name=validated_data['nickname'],
                      ico=ContentFile(decoded_file, complete_file_name), phone_number=validated_data['phone'])
        user.set_password(password)
        user.save()

        return user

class SettingSerializer(serializers.Serializer):
    no_disturb = serializers.BooleanField(required=False)

class CompanySerializer(serializers.Serializer):
    name = serializers.CharField()
    copyright = serializers.CharField()
    phone = serializers.CharField()
    website = serializers.CharField()
    wx_account = serializers.CharField()

class VersionSerializer(serializers.Serializer):
    type = serializers.CharField()
    version = serializers.CharField()

class VersionResponseSerializer(serializers.Serializer):
    upgrade = serializers.BooleanField()
    force = serializers.BooleanField(required=False)

class ShopComboGoodsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ShopComboGoods
        fields = ('id', 'name', 'price', 'num', 'unit')
        read_only_fields = ('id', )

class WalletVerifyPayPwSerializer(serializers.Serializer):
    pay_password = serializers.CharField()

class BankcardSerializer(serializers.Serializer):
    bank_name = serializers.CharField()
    card_type = serializers.CharField()
    simple_card = serializers.CharField()
    ico = CompressBase64ImageField(required=False)

class RelieveBankcardSerializer(serializers.Serializer):
    pay_password = serializers.CharField()

class WalletSetPayPwSerializer(serializers.Serializer):
    verification_code = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        try:
            obj = SmsVerCode.objects.filter(phone=self.username).order_by('-id')[0]
        except:
            raise ValidationDict211Error('验证码未找到.')

        code = obj.code
        expire_time = obj.expire_time

        if code !=attrs['verification_code']:
            raise ValidationDict211Error('验证码不匹配.')
        elif expire_time < timezone.now():
            raise ValidationDict211Error('验证码已过期.')

        try:
            user = MyUser.objects.get(username=self.username)
        except MyUser.DoesNotExist:
            raise ValidationDict211Error('用户名不存在.')
        if not user.is_active:
            raise ValidationDict211Error('该用户被锁定.')

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致.')

        obj.obsolete = True
        obj.save(update_fields=['obsolete'])

        return attrs

class WalletModifyPayPwSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationDict211Error('两次密码不一致')
        attrs.pop('confirm_password')
        return attrs

class JudgeSerializer(serializers.Serializer):
    judge = serializers.BooleanField()

class CardDiscountSerializer(serializers.ModelSerializer):

    class Meta:
        model = CardDiscount
        fields = ('discount', )

class AbstractCashRecordListSerializer(serializers.ModelSerializer):
    request_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = AbstractCash
        fields = ('id', 'request_time', 'cash', 'status')

class TempSerializer(serializers.Serializer):
    time = serializers.IntegerField()
    text = serializers.CharField()

class AbstractCashRecordSerializer(serializers.ModelSerializer):
    cash = serializers.SerializerMethodField()
    charge = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    request_acc_no = serializers.SerializerMethodField()
    trace = serializers.SerializerMethodField()

    def get_trace(self, obj):
        temps = []

        if obj.request_time:
            temp = TempSerializer()
            temp.time = timetuple(obj.request_time)
            if obj.status == 'wait':
                temp.text = dict(list(AbstractCash.STATUS))['wait']
            else:
                temp.text = dict(list(AbstractCash.STATUS))['request']
            temps.append(temp)

        if obj.handle_time:
            temp = TempSerializer()
            temp.time = timetuple(obj.handle_time)
            temp.text = dict(list(AbstractCash.STATUS))['apply']
            temps.append(temp)

        if obj.bank_time:
            temp = TempSerializer()
            temp.time = timetuple(obj.bank_time)
            temp.text = obj.get_status_display()
            temps.append(temp)

        return TempSerializer(temps, many=True).data

    def get_request_time(self, obj):
        return timetuple(obj.request_time)

    def get_handle_time(self, obj):
        return timetuple(obj.handle_time)

    def get_bank_time(self, obj):
        return timetuple(obj.bank_time)

    def get_cash(self, obj):
        return decimal2string(obj.cash - obj.charge)

    def get_charge(self, obj):
        return decimal2string(obj.charge)

    def get_status(self, obj):
        return obj.get_status_display()

    def get_request_acc_no(self, obj):
        return obj.request_acc_no[-4:]

    class Meta:
        model = AbstractCash
        fields = ('id', 'cash', 'charge', 'status', 'trace',
                  'request_bank_name', 'request_acc_no')

class TradePayResponseSerializer(serializers.Serializer):
    sign = serializers.CharField(required=False)
    url = serializers.CharField(required=False)
    content = serializers.CharField(required=False)
    remain = serializers.CharField(required=False)#DecimalField(max_digits=10, decimal_places=2, required=False)
    type = serializers.IntegerField(required=False)
    fy_wx_openid_url = serializers.CharField(required=False)
    ali_trade_no = serializers.CharField(required=False)

class PayTypeRequestSerializer(serializers.Serializer):
    PLATFORM_TYPE = (
        ('app', 'app'),
        ('account', 'account'),
        ('wap', 'wap')
    )

    platform_type = serializers.ChoiceField(choices=PLATFORM_TYPE)

    PAY_TYPE = (
        ('wx', 'weixin'),
        ('ali', 'zhifubao'),
        ('qq', 'qq')
    )

    pay_type = serializers.ChoiceField(choices=PAY_TYPE)

class PayTypeResponseSerializer(serializers.Serializer):
    type = serializers.IntegerField(required=False)
    fy_wx_openid = serializers.BooleanField(required=False)

class FyWxAccountPaySerializer(serializers.Serializer):
    url = serializers.URLField()

class ShopFaceSerializer(MyModelSerializer):
    face = CompressBase64ImageField()

    class Meta:
        model = Shop
        fields = ('face', )

class ShopPhotoAddListSerializer(serializers.Serializer):
    class ShopPhotoInnerSerializer(serializers.Serializer):
        photo = serializers.CharField()

    photos = ShopPhotoInnerSerializer(many=True)

    def save(self, validated_data):
        ret=[]
        for item in validated_data['photos']:
            serializer = ShopPhotoSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            ret.append(serializer.save(shop=validated_data['shop']))
        return ret

class LatitudeFilterSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=14, decimal_places=12, required=False)
    longitude = serializers.DecimalField(max_digits=15, decimal_places=12, required=False)

class LatitudeReqireFilterSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=14, decimal_places=12)
    longitude = serializers.DecimalField(max_digits=15, decimal_places=12)
