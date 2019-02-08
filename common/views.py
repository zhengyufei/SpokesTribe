import random, json

import rest_framework.exceptions
from django.db import connection,transaction
from django.db.models import Q
from packaging import version
from rest_framework import parsers, renderers, viewsets, permissions, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from rest_framework.views import APIView

import SpokesTribe.settings as settings
from IM.IM import IM as im
from IM.usersig import sig
from Logger.logger import Logger
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl
from .function import register_profile
from .models import ShopFirstType, MyUser, NationalId, SmsVerCode, Feedback, Friend, FriendGroup, \
    RandomNickImage, MyUserThirdProfile, CurrentVersion, Shop, ShopPayFYProfile
from .serializers import AuthTokenSerializer, UserCreateSerializer, ShopTypeSerializer, UserNormalInfoSerializer,\
    UserNationalIdSerializer, FindPasswordSerializer, SmsVerifySerializer, RegisterUsernameVerifySerializer,\
    FeedbackSerializer, ResetPasswordSerializer, FriendConfirmSerializer, FriendAliasSerializer,\
    FriendChangeGroupSerializer, PureSmsVerifySerializer, EmptySerializer, ThirdLoginSerializer, ThirdBindSerializer, ThirdRegisterSerializer, \
    SettingSerializer, VersionSerializer, VersionResponseSerializer, ThirdBind2Serializer, ThirdBind3Serializer, CompanySerializer, \
    PayTypeRequestSerializer, PayTypeResponseSerializer, FyWxAccountPaySerializer
from Pay.Ali.alipay import BuyerPay
from Pay.Integrated.Fuyou import FuyouPay


# Create your views here.
class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        try:
            MyUser.objects.get(username=user)
        except MyUser.DoesNotExist:
            raise ValidationDict211Error("该用户不存在")

        token, created = Token.objects.get_or_create(user=user)
        user = MyUser.objects.get(username=user)
        return Response({'token': token.key, 'im_account': str(user.id), 'im_pw': sig(str(user.id)),
            'apns_alias' : str(user.id)})

obtain_auth_token = ObtainAuthToken.as_view()

class SmsVerifyViewSet(mixins.CreateModelMixin,
                                viewsets.GenericViewSet):
    queryset = SmsVerCode.objects.all()
    permission_classes = [permissions.AllowAny, ]
    serializer_class = SmsVerifySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        type = serializer.validated_data['type']
        code = serializer.validated_data['code'] = random.randint(100000, 999999)
        serializer.save(serializer.validated_data)
        self.send_sms(serializer.validated_data['phone'], type=type, code=code)

        return Response({'detail': 'OK'})

    def base_send_sms(self, sms, phone, type, code):
        if type is 1:
            sms.register_sms(phone=phone, code=code)
        elif type is 2:
            sms.confirm_sms(phone=phone, code=code)
        elif type is 3:
            if MyUser.objects.filter(username=phone).exists():
                sms.register_sms(phone=phone, code=code)
            else:
                sms.confirm_sms(phone=phone, code=code)

    @list_route(methods=['post'])
    def register_username_verify(self, request, *args, **kwargs):
        serializer = RegisterUsernameVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({'detail': 'OK'})

    @list_route(methods=['post'])
    def verify(self, request, *args, **kwargs):
        serializer = PureSmsVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({'detail': 'OK'})

class FindPasswordViewSet(mixins.CreateModelMixin,
    viewsets.GenericViewSet):
    queryset = SmsVerCode.objects.all()
    permission_classes = [permissions.AllowAny, ]
    serializer_class = FindPasswordSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(serializer.validated_data)

        return Response({'detail': 'OK'})

class UserCreateViewSet(mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    queryset = MyUser.objects.all()
    permission_classes = [permissions.AllowAny, ]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except rest_framework.exceptions.ValidationError as e:
            for k,v in e.detail.items():
                if k == 'username' and v == ['A user with that username already exists.']:
                    raise ValidationDict211Error('该用户已注册')

        temp = RandomNickImage.objects.all().order_by('?')[0]
        user = serializer.save(serializer.validated_data, temp.nick, temp.image)
        register_profile(request, user)

        return Response({'result': 'OK'})

class ShopTypeViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = ShopFirstType.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

class ShopViewSet(mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = EmptySerializer

    @detail_route(methods=['post'])
    def pay_type(self, request, pk=None):
        serializer = PayTypeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        platform_type = serializer.validated_data['platform_type']
        pay_type = serializer.validated_data['pay_type']

        serializer = PayTypeResponseSerializer()
        if platform_type == 'account':
            shop = Shop.objects.get(pk=pk)
            if shop.pay_type == 1:
                if pay_type == 'wx':
                    serializer.type = 6
                elif pay_type == 'ali':
                    serializer.type = 7
            elif shop.pay_type == 2:
                if pay_type == 'wx':
                    serializer.type = 8
                    if not shop.fuyou.is_wx_oasis:
                        serializer.fy_wx_openid = True if request.user.get_third().fy_wx_openid else False
                    else:
                        serializer.fy_wx_openid = True if request.user.get_third().fy_wx_oasis_openid else False
                elif pay_type == 'ali':
                    serializer.type = 9

        serializer = PayTypeResponseSerializer(serializer)

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def fy_wx_account_pay(self, request, pk=None):
        serializer = FyWxAccountPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fuyou = ShopPayFYProfile.objects.get(pk=pk)

        temp = FuyouPay.Openid(fuyou.merchant_no, fuyou.terminal_id, fuyou.access_token,
                               serializer.validated_data['url'])
        serializer = FyWxAccountPaySerializer({'url': temp.get_url()})

        return Response(serializer.data)

class UserNormalInfoViewSet(mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = UserNormalInfoSerializer

    def create(self, request, *args, **kwargs):
        is_im_syn = settings.IM_ONLINE and ('nick_name' in request.data or 'ico' in request.data)

        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        if is_im_syn:
            im.modify_nick(request.user.id, request.user.nick_name)
            im.modify_ico(request.user.id, GetAbsoluteImageUrl(request, request.user.ico_thumbnail))

        return Response({'result': 'OK'})

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)

        return Response(serializer.data)

    @list_route(methods=['post'])
    def reset_password(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response({'detail': 'OK'})

class UserNationalIdViewSet(mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    queryset = NationalId.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = UserNationalIdSerializer

    def create(self, request, *args, **kwargs):
        try:
            national_id = NationalId.objects.get(user=request.user)
            if national_id.is_valid:
                raise ValidationDict211Error('实名制已锁定')
            serializer = self.get_serializer(national_id, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
        except NationalId.DoesNotExist:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

        return Response({'result': 'OK'})

    def list(self, request, *args, **kwargs):
        try:
            national_id = NationalId.objects.get(user=request.user)
        except NationalId.DoesNotExist:
            return Response({})

        serializer = self.get_serializer(national_id)

        return Response(serializer.data)

class FeedbackViewSet(mixins.CreateModelMixin,
                       viewsets.GenericViewSet):
    queryset = Feedback.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = FeedbackSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        return Response({'detail': 'OK'})

class FriendViewSet(viewsets.GenericViewSet):
    queryset = Friend.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = FriendConfirmSerializer #temp

    @list_route(methods=['post'])
    def confirm_friend(self, request, *args, **kwargs):
        serializer = FriendConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            friend=MyUser.objects.get(id=serializer.validated_data['friend'])
        except MyUser.DoesNotExist:
            raise ValidationDict211Error('用户未找到')

        user = request.user
        im.add_friend(user.id, friend.id)

        try:
            group=FriendGroup.objects.get(user=user, type=1)
            Friend.objects.create(user=user, friend=friend, group=group)

            group = FriendGroup.objects.get(user=friend, type=1)
            Friend.objects.create(user=friend, friend=user, group=group)
        except:
            pass

        return Response({'detail': 'OK'})

    @list_route(methods=['post'])
    def change_group(self, request, *args, **kwargs):
        serializer = FriendChangeGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Friend.objects.filter(user=request.user, friend__id__in=serializer.validated_data['friends'])\
            .update(group=FriendGroup.objects.get(user=request.user, type=serializer.validated_data['type']))

        return Response({'detail': 'OK'})

    @detail_route(methods=['post'])
    def alias(self, request, pk=None):
        serializer = FriendAliasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Friend.objects.filter(user=request.user, friend__id=pk).update(alias=serializer.validated_data['alias'])

        return Response({'detail': 'OK'})

    @detail_route(methods=['get'])
    def delete(self, request, pk=None):
        im.del_friend(request.user.id, pk)

        try:
            Friend.objects.filter((Q(user=request.user) & Q(friend__id=pk))
                                  | (Q(user__id=pk) & Q(friend=request.user))).delete()
        except MyUser.DoesNotExist:
            pass#raise ValidationDict211Error('用户未找到')

        return Response({'detail': 'OK'})

class ThirdViewSet(viewsets.GenericViewSet):
    queryset = Friend.objects.none()
    permission_classes = [permissions.AllowAny, ]
    serializer_class = EmptySerializer

    unionid = ''

    def get_prifile(self, unionid):
        return MyUserThirdProfile.objects.get(**{self.unionid:unionid})

    def create_prifile(self, user, unionid):
        return MyUserThirdProfile.objects.create(**{'user':user, self.unionid:unionid})

    def has_unionid(self, third, unionid):
        return third.__dict__[self.unionid] == unionid

    def set_unionid(self, third, unionid):
        MyUserThirdProfile.objects.filter(**{self.unionid:unionid}).update(**{self.unionid:None})
        self.set_unionid2(third, unionid)

    def set_unionid2(self, third, unionid):
        third.__dict__[self.unionid] = unionid
        third.save(update_fields=[self.unionid])

    def get_unionid(self, third):
        return third.__dict__[self.unionid]

    @list_route(methods=['post'])
    def login(self, request, *args, **kwargs):
        serializer = ThirdLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            profile = self.get_prifile(serializer.validated_data['unionid'])
            if not profile.user.phone_number:
                return Response({'flag': False})
        except MyUserThirdProfile.DoesNotExist:
            return Response({'flag': False})

        token, created = Token.objects.get_or_create(user_id=profile.user_id)
        return Response({'flag': True, 'token': token.key, 'username': profile.user.username,
                         'im_account': str(profile.user.id), 'im_pw': sig(str(profile.user.id)),
                         'apns_alias' : str(profile.user.id)})

    @list_route(methods=['post'])
    def third_login(self, request, *args, **kwargs):
        serializer = ThirdLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unionid = serializer.validated_data['unionid']

        try:
            profile = self.get_prifile(unionid)
            user = profile.user
        except MyUserThirdProfile.DoesNotExist:
            try:
                with transaction.atomic():
                    user = serializer.save(serializer.validated_data)
            except:
                del serializer.validated_data['nickname']
                user = serializer.save(serializer.validated_data)
                Logger.Log('error', 'nick error')

            self.create_prifile(user, unionid)
            register_profile(request, user)

        token, created = Token.objects.get_or_create(user=user)
        return Response({'token':token.key})

    @list_route(methods=['post'])
    def bind(self, request, *args, **kwargs):
        serializer = ThirdBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unionid = serializer.validated_data['unionid']
        phone = serializer.validated_data['phone']

        has_user = None
        has_third = None

        try:
            user = MyUser.objects.get(username=phone)
            has_user = True
        except:
            pass

        if has_user:
            third = user.get_third()
            if self.has_unionid(third, unionid):
                raise ValidationDict211Error('已经绑定')
            else:
                self.set_unionid(third, unionid)

            token, created = Token.objects.get_or_create(user=user)
            return Response({'flag': True, 'token': token.key, 'username': user.username,
                             'im_account': str(user.id), 'im_pw': sig(str(user.id)),
                             'apns_alias': str(user.id)})

        try:
            profile = self.get_prifile(unionid)
            has_third = True
        except:
            pass

        if has_third:
            if not profile.user.phone_number:
                profile.user.username = phone
                profile.user.phone_number = phone
                profile.user.save(update_fields=['username', 'phone_number'])

            token, created = Token.objects.get_or_create(user=profile.user)
            return Response({'flag': True, 'token': token.key, 'username': profile.user.username,
                             'im_account': str(profile.user.id), 'im_pw': sig(str(profile.user.id)),
                             'apns_alias': str(profile.user.id)})

        return Response({'flag': False})

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def third_bind(self, request, *args, **kwargs):
        serializer = ThirdBind2Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        third = request.user.get_third()
        if not third:
            raise ValidationDict211Error('第三方未登陆')

        unionid = self.get_unionid(third)
        phone = serializer.validated_data['phone']

        has_user = None
        has_third = None

        try:
            user = MyUser.objects.get(username=phone)
            has_user = True
        except:
            pass

        if has_user:
            third = user.get_third()
            if self.has_unionid(third, unionid):
                raise ValidationDict211Error('已经绑定')
            else:
                self.set_unionid(third, unionid)

            token, created = Token.objects.get_or_create(user=user)
            return Response({'flag': True, 'token': token.key, 'username': user.username,
                            'im_account': str(user.id), 'im_pw': sig(str(user.id))})

        try:
            profile = self.get_prifile(unionid)
            has_third = True
        except:
            pass

        if has_third:
            if not profile.user.phone_number:
                profile.user.username = phone
                profile.user.phone_number = phone
                profile.user.save(update_fields=['username', 'phone_number'])

            token, created = Token.objects.get_or_create(user=profile.user)
            return Response({'flag': True, 'token': token.key, 'username': profile.user.username,
                             'im_account': str(profile.user.id), 'im_pw': str(sig(profile.user.id))})

        return Response({'flag': False})

    @list_route(methods=['post'])
    def register(self, request, *args, **kwargs):
        serializer = ThirdRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(serializer.validated_data)

        third = user.get_third()
        if self.get_unionid(third):
            raise ValidationDict211Error('已经绑定')
        else:
            self.set_unionid2(third, serializer.validated_data['unionid'])

        register_profile(request, user)

        token, created = Token.objects.get_or_create(user=user)
        return Response({'flag':True, 'token': token.key, 'username': user.username,
                         'im_account': user.id, 'im_pw': sig(user.id),
                         'apns_alias' : user.id})

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_friend(self, request, *args, **kwargs):
        friend_id = request.data['spokesman_id']
        if request.user.id == int(friend_id) or Friend.objects.filter(user_id=friend_id, friend=request.user).exists():
            return Response({'result': 'OK'})

        group = FriendGroup.objects.get(user=request.user, type=3)
        Friend.objects.create(user=request.user, friend_id=friend_id, group=group)

        group = FriendGroup.objects.get(user_id=friend_id, type=3)
        Friend.objects.create(user_id=friend_id, friend=request.user, group=group)

        im.add_friend_one_side(request.user.id, friend_id)
        im.add_friend_one_side(friend_id, request.user.id)

        return Response({'result': 'OK'})

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bind_unionid(self, request, *args, **kwargs):
        serializer = ThirdBind3Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unionid = serializer.validated_data['unionid']

        if not request.user.phone_number:
            raise ValidationDict211Error('no phone number')

        third = None
        try:
            third = MyUserThirdProfile.objects.get(**{self.unionid: unionid})
        except MyUserThirdProfile.DoesNotExist:
            pass

        if third:
            if third.user.phone_number:
                raise ValidationDict211Error('第三方已经被绑定过')
            else:
                third.__dict__[self.unionid] = None
                third.save(update_fields=[self.unionid])

        self.set_unionid2(request.user.third, unionid)

        return Response({'detail': 'OK'})

class WeixinViewSet(ThirdViewSet):
    unionid = 'weixin_unionid'

class QQViewSet(ThirdViewSet):
    unionid = 'qq_unionid'

class WeiboViewSet(ThirdViewSet):
    unionid = 'weibo_unionid'

class ZhifubaoViewSet(ThirdViewSet):
    unionid = 'zhifubao_unionid'

    @list_route(methods=['get'])
    def auth(self, request, *args, **kwargs):
        response = BuyerPay().auth(request.user.id)
        return Response({'result':response})

class SettingViewSet(viewsets.GenericViewSet):
    queryset = Friend.objects.none()
    permission_classes = [permissions.AllowAny]
    serializer_class = SettingSerializer

    @list_route(methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def no_disturb(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'no_disturb' in serializer.validated_data.keys():
            request.user.myusersettingprofile.no_disturb = serializer.validated_data['no_disturb']
            request.user.myusersettingprofile.save(update_fields=['no_disturb'])

        return Response({'result': 'OK'})

    @list_route(methods=['post'])
    def version(self, request, *args, **kwargs):
        serializer = VersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version1 = version.parse(serializer.validated_data['version'])
        cur_version = CurrentVersion.objects.filter(type=serializer.validated_data['type'])[0].version

        serializer = VersionResponseSerializer()
        serializer.upgrade = version1 < version.parse(cur_version.version)
        serializer.force = version1 < version.parse(cur_version.min_version)

        serializer = VersionResponseSerializer(serializer)

        return Response(serializer.data)

class AboutViewSet(viewsets.GenericViewSet):
    queryset = Friend.objects.none()
    permission_classes = [permissions.AllowAny]
    serializer_class = CompanySerializer

    @list_route(methods=['get'])
    def company(self, request, *args, **kwargs):
        serializer = CompanySerializer()

        serializer.name = '成都脸王科技有限公司'
        serializer.copyright = 'copyright\u00a92016-2017'
        serializer.phone = '028-67878860'
        serializer.website = 'http://www.dailibuluo.com'
        serializer.wx_account = 'www_dailibuluo_com'

        serializer = CompanySerializer(serializer)

        return Response(serializer.data)

