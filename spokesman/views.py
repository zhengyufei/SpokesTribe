import decimal
import json
from math import ceil, floor

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

import SpokesTribe.settings as settings
import common.views
from Bankcard.bankcard import verify_bankcard
from IM.IM import IM as im
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl, sql_execute, calcDistance
from Pay.Zhaoshang.ZhaoshangTransfer import PayForAnother
from SMS import SMS
from SpokesTribe.settings import BROTHER_RATIO1, BROTHER_RATIO2
from common.function import discount_describe_brother, discount_describe_friend, response_page, response_list
from common.models import MyUser, Shop, SpokesmanResume, ShopSpoke, CollectShop,\
    Wallet, ShopPhoto, ShopSpokeGroup, ShopDiscount, \
    MyUserSpokeProfile, BankCard, Comment, CashRecord, TradeTicketProfile, ShopMember, \
    Flyer2User, ShopFlyerDiscountProfile, ShopFlyerReduceProfile, ShopFlyerExperienceProfile
from common.permission import per_phone_number
from common.serializers import ShopPhotoSerializer, DelIDsSerializer, EmptySerializer,\
    WalletSetPayPwSerializer, WalletModifyPayPwSerializer, RelieveBankcardSerializer, \
    BankcardSerializer, WalletVerifyPayPwSerializer, LatitudeFilterSerializer
from .permission import HasPayPassword
from .serializers import SpokesmanResumeSerializer, ShopSpokeSerializer, WalletLooseChangeSerializer, FriendDetailSerializer, \
    FriendSpokesShopSerializer, FriendSpokesShopDetailSerializer, SpokesShopSerializer, SpokesShopRequestListSerializer, \
    SpokesShopGroupDiscountSerializer, Interface1Serializer, ShopCommentSerializer, CashSerializer, BindBankcardSerializer, \
    SearchFriendSerializer, FriendListSerializer, HasPhoneSerializer, ThirdAuthSerializer, \
    ShopFlyerSerializer, ShopFlyerDiscountProfileSerializer, ShopFlyerReduceProfileSerializer, ShopFlyerExperienceProfileSerializer


class SmsVerifyViewSet(common.views.SmsVerifyViewSet):

    def send_sms(self, phone, type, code):
        sms = SMS.SpokesmanSMS()
        self.base_send_sms(sms, phone, type, code)

class ShopCommentViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopCommentSerializer

    def list(self, request, *args, **kwargs):
        queryset = Comment.objects.filter(trade__shop__id=kwargs['pk_shop'])

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        return Response({'results': serializer.data})

class ShopPhotoViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = ShopPhoto.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopPhotoSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopPhoto.objects.filter(shop=kwargs['pk_shop'])

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response({'results':serializer.data})

class ResumeViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = SpokesmanResume.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = SpokesmanResumeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resume = SpokesmanResume.objects.get(user=request.user)
            serializer = self.get_serializer(resume, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
        except SpokesmanResume.DoesNotExist:
            serializer.save(user=request.user)

        return Response({'result': 'OK'})

    def list(self, request, *args, **kwargs):
        try:
            resume = SpokesmanResume.objects.get(user=request.user)
        except SpokesmanResume.DoesNotExist:
            resume = SpokesmanResume()
            resume.user = request.user
            resume.work = ''
            resume.resume = ''

        serializer = self.get_serializer(resume)

        return Response(serializer.data)

class ShopSpokesViewSet(mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = ShopSpoke.objects.all()
    permission_classes = [permissions.IsAuthenticated,]
    serializer_class = ShopSpokeSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopSpoke.objects.filter(Q(spokesman=request.user) | Q(member__user=request.user))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            temp = ShopSpoke.objects.get(Q(shop_id=kwargs['pk']) & (Q(spokesman=request.user) | Q(member__user=request.user)))
        except ShopSpoke.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        self.kwargs['pk'] = str(temp.id)

        return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        shop = Shop.objects.get(pk=kwargs['pk'])

        if ShopMember.objects.filter(shop_id=kwargs['pk'], user=request.user).exists():
            raise ValidationDict211Error('不能取消会员的代理', detail_en='can`t cancel member')

        if shop.managers.filter(id=kwargs['pk']).exists():
            raise ValidationDict211Error('不能取消管理员的代理', detail_en='can`t cancel manager')

        try:
            ShopSpoke.objects.get(Q(shop_id=kwargs['pk']) & (Q(spokesman=request.user) | Q(member__user=request.user))).delete()
            ShopSpokeGroup.objects.get(group__user=request.user, group__type=3, shop_id=kwargs['pk']).delete()
        except ShopSpoke.DoesNotExist or ShopSpokeGroup.DoesNotExist:
            raise ValidationDict211Error('没有权限')

        shop.spoke_count -= 1
        shop.save(update_fields=['spoke_count'])

        return Response({'result': 'OK'})

    def sql_normal(self, user_id):
        sql = "SELECT 'normal', S.id, S.name, S.ico_thumbnail, S.address, S.type_id, S.custom_type, S.`level`, S.`describe`, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price, S3.discount, U.major_shop_id "\
            "FROM common_shopspoke AS S2 "\
            "LEFT JOIN common_shop AS S ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopactivity AS A ON S2.shop_id = A.shop_id "\
            "LEFT JOIN common_shopdiscount AS D ON S2.shop_id = D.shop_id "\
            "LEFT JOIN common_myuserspokeprofile AS U ON S.id = U.major_shop_id AND S2.spokesman_id = U.user_id "\
            "LEFT JOIN common_friendgroup AS G ON S2.spokesman_id = G.user_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = G.id "\
            "WHERE S2.spokesman_id = {0} AND S3.shop_id = S2.shop_id AND S2.type = 'normal' "\
            .format(user_id)

        return sql

    def sql_member(self, user_id):
        sql = "SELECT 'member', S.id, S.name, S.ico_thumbnail, S.address, S.type_id, S.custom_type, S.`level`, S.`describe`, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price, " \
            "S3.member_discount, U.major_shop_id "\
            "FROM common_shopspoke AS S2 "\
            "LEFT JOIN common_shop AS S ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopactivity AS A ON S2.shop_id = A.shop_id "\
            "LEFT JOIN common_shopmember AS M ON S2.shop_id = M.shop_id AND S2.member_id = M.id "\
            "LEFT JOIN common_shopmembercard AS M2 ON M2.id = M.member_card_id "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "LEFT JOIN common_myuserspokeprofile AS U ON S.id = U.major_shop_id AND M.user_id = U.user_id "\
            "LEFT JOIN common_friendgroup AS G ON M.user_id = G.user_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = G.id "\
            "WHERE M.user_id = {0} AND M.loose_change > 0 AND S3.shop_id = S2.shop_id AND S2.type = 'member' "\
            .format(user_id)

        return sql

    def fill(self, request, obj):
        serializer = SpokesShopSerializer()
        serializer.id = obj[1]
        serializer.name = obj[2]
        serializer.ico = GetAbsoluteImageUrl(request, obj[3])
        serializer.address = obj[4]
        serializer.type = obj[5]
        serializer.custom_type = obj[6]
        serializer.level = obj[7]
        serializer.describe = obj[8]
        if obj[9]:
            if 1 == obj[10]:
                serializer.activity = '商家活动{0}折'.format(obj[11] / 10)
            elif 2 == obj[10]:
                serializer.activity = '商家活动满{0}减{1}元'.format(obj[12], obj[13])

        if obj[14]:
            serializer.discount_type = obj[15]
            if 1 == serializer.discount_type:
                if obj[16]:
                    serializer.discount = ceil(int(obj[16]) * BROTHER_RATIO1) + BROTHER_RATIO2
                    serializer.bonus = serializer.discount - obj[16]
                else:
                    serializer.discount = 100
                    serializer.bonus = 0
            elif 2 == serializer.discount_type:
                serializer.full_price = obj[17]
                serializer.reduce_price = floor(int(obj[18]) * BROTHER_RATIO1)
                serializer.bonus = serializer.full_price - serializer.reduce_price

            serializer.friend_discount = obj[19]
        if obj[20]:
            serializer.major = True
        serializer.spokesman_id = request.user.id

        return serializer

    def sql_member_list(self, shop_id, user_id):
        return self.sql_member(user_id) + " AND M.loose_change > 0"

    def get_list(self, request):
        f1 = sql_execute(self.sql_normal(request.user.id))
        f2 = sql_execute(self.sql_member(request.user.id))

        fetchall = []
        fetchall.extend(list(f1))
        fetchall.extend(list(f2))

        major_serializer = None
        serializers = []

        for obj in fetchall:
            serializer = self.fill(request, obj)

            if hasattr(serializer, 'major'):
                major_serializer = serializer
            else:
                serializers.append(serializer)

        if major_serializer:
            serializers.insert(0, major_serializer)

        queryset = serializers
        serializer = SpokesShopSerializer(queryset, many=True)
        return Response({'results': serializer.data})

    def sql_normal_single(self, shop_id, user_id):
        return self.sql_normal(user_id) + " AND S.id = {0}".format(shop_id)

    def sql_member_single(self, shop_id, user_id):
        return self.sql_member(user_id) + " AND S.id = {0}".format(shop_id)

    def get_single(self, request, shop_id):
        fetchall = sql_execute(self.sql_normal_single(shop_id, request.user.id))
        if 0 == len(fetchall):
            fetchall = sql_execute(self.sql_member_single(shop_id, request.user.id))

        serializer = None

        for obj in fetchall:
            serializer = self.fill(request, obj)

        if not serializer:
            raise ValidationDict211Error('不是代言人')

        serializer = SpokesShopSerializer(serializer)
        return Response(serializer.data)

    @list_route(methods=['get'])
    def spokes_list(self, request, *args, **kwargs):
        return self.get_list(request)

    @detail_route(methods=['get'])
    def spokes(self, request, pk=None):
        return self.get_single(request, pk)

    @list_route(methods=['get'])
    def request_list(self, request, *args, **kwargs):
        sql = "SELECT S2.id, S2.name, S2.ico_thumbnail, S2.address, S2.type_id, S2.custom_type, S2.`level`, S2.`describe`, "\
                "S3.require1, S3.require2, S3.require3, S1.request_time, NULL AS handle_time, '申请中' AS result "\
                "FROM common_shopspokerequest AS S1 " \
                "LEFT JOIN common_spokesmanresume AS R ON S1.resume_id = R.user_id " \
                "LEFT JOIN common_shop AS S2 ON S1.shop_id = S2.id "\
                "LEFT JOIN common_shoprequire AS S3 ON S1.shop_id = S3.shop_id "\
                "WHERE R.user_id = {0} "\
                "UNION ALL "\
                "SELECT S2.id, S2.name, S2.ico, S2.address, S2.type_id, S2.custom_type, S2.`level`, S2.`describe`, "\
                "S3.require1, S3.require2, S3.require3, S1.request_time, S1.handle_time, '失败' as result "\
                "FROM common_shopspokerequesthistory AS S1 "\
                "LEFT JOIN common_shop AS S2 ON S1.shop_id = S2.id " \
                "LEFT JOIN common_shoprequire AS S3 ON S1.shop_id = S3.shop_id "\
                "WHERE S1.spokesman_id = {0} AND S1.result = 0".format(request.user.id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        queryset = []

        for obj in fetchall:
            serializer = SpokesShopRequestListSerializer()
            serializer.id = obj[0]
            serializer.name = obj[1]
            serializer.ico = GetAbsoluteImageUrl(request, obj[2])
            serializer.address = obj[3]
            serializer.type = obj[4]
            serializer.custom_type = obj[5]
            serializer.level = obj[6]
            serializer.describe = obj[7]
            serializer.require1 = obj[8]
            serializer.require2 = obj[9]
            serializer.require3 = obj[10]
            serializer.request_time = obj[11].date()
            if obj[12]:
                serializer.handle_time = obj[12].date()
            serializer.result = obj[13]

            queryset.append(serializer)

        return response_list(self, SpokesShopRequestListSerializer, queryset)

    @detail_route(methods=['post'])
    def set_friend_discount(self, request, pk=None):
        serializer = SpokesShopGroupDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discount = serializer.validated_data['discount']
        spoke = ShopSpoke.objects.get(Q(shop_id=pk) & (Q(spokesman=request.user) | Q(member__user=request.user)))
        if 'normal' == spoke.type:
            self.set_friend_normal_discount(request, pk, discount)
        elif 'member' == spoke.type:
            self.set_friend_member_discount(request, pk, discount)

        return Response({'result': 'OK'})

    def set_friend_normal_discount(self, request, pk, discount):
        shop_discount = ShopDiscount.objects.get(pk=pk)

        temp, temp2 = discount_describe_brother(**shop_discount.__dict__)

        if not shop_discount.is_valid or not temp:
            raise ValidationDict211Error('商家未设返佣')
        elif shop_discount.type == 1 and (temp > discount or discount > 100):
            raise ValidationDict211Error('超出范围')
        elif shop_discount.type == 2 and (temp < discount or discount < 0):
            raise ValidationDict211Error('超出范围')

        ShopSpokeGroup.objects.filter(group__user=request.user, group__type=3, shop_id=pk).update(discount=discount)

    def set_friend_member_discount(self, request, pk, discount):
        card = ShopMember.objects.get(shop_id=pk, user=request.user).member_card

        if not hasattr(card, 'discount'):
            raise ValidationDict211Error('商家未设返佣')

        temp, temp2 = discount_describe_brother(True, **card.discount.__dict__)

        if not temp:
            raise ValidationDict211Error('商家未设返佣')

        if not hasattr(card, 'discount') or temp > discount or discount > 100:
            raise ValidationDict211Error('超出范围')

        ShopSpokeGroup.objects.filter(group__user=request.user, group__type=3, shop_id=pk).update(member_discount=discount)

    @detail_route(methods=['post'])
    def set_major_shop(self, request, pk=None):
        if not MyUserSpokeProfile.objects.filter(user=request.user).update(major_shop_id=pk):
            MyUserSpokeProfile.objects.create(user=request.user, major_shop_id=pk, level=0)

        is_im_syn = settings.IM_ONLINE

        if is_im_syn:
            im.modify_major_spokes(request.user.id, Shop.objects.get(pk=pk).type.name)

        return self.get_list(request)

class CollectShopViewSet(mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = CollectShop.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmptySerializer

    @list_route(methods=['post'])
    def del_shops(self, request, pk=None):
        serializer = DelIDsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        CollectShop.objects.filter(user=request.user, shop_id__in=serializer.validated_data['ids']).delete()

        return Response({'result': 'OK'})

    def destroy(self, request, *args, **kwargs):
        if not CollectShop.objects.filter(user=request.user, pk=kwargs['pk']).exists():
            raise ValidationDict211Error('没有权限')
        return mixins.DestroyModelMixin.destroy(self, request, *args, **kwargs)

class WalletViewSet(viewsets.GenericViewSet):
    queryset = Wallet.objects.all()
    permission_classes = [permissions.IsAuthenticated,]
    serializer_class = WalletLooseChangeSerializer

    @list_route(methods=['get'])
    def info(self, request, *args, **kwargs):
        wallet = Wallet.objects.get(user=request.user)
        serializer = WalletLooseChangeSerializer(wallet)

        return Response(serializer.data)

    @list_route(methods=['post'])
    @per_phone_number
    def set_pay_pw(self, request, *args, **kwargs):
        serializer = WalletSetPayPwSerializer(data=request.data)
        serializer.username = request.user.username
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(user=request.user)

        if wallet.has_usable_password():
            raise ValidationDict211Error('支付密码已经设置')

        wallet.set_password(serializer.validated_data['new_password'])
        wallet.save(update_fields=['password'])

        return Response({'result': 'OK'})

    @list_route(methods=['post'])
    def modify_pay_pw(self, request, *args, **kwargs):
        serializer = WalletModifyPayPwSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(user=request.user)

        if not wallet.check_password(serializer.validated_data['old_password']):
            raise ValidationDict211Error('旧密码错误')

        wallet.set_password(serializer.validated_data['new_password'])
        wallet.save(update_fields=['password'])

        return Response({'result': 'OK'})

    @list_route(methods=['post'])
    def verify_pay_pw(self, request, *args, **kwargs):
        serializer = WalletVerifyPayPwSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(user=request.user)

        if not wallet.check_password(serializer.validated_data['pay_password']):
            raise ValidationDict211Error('密码错误')

        return Response({'result': 'OK'})

    @list_route(methods=['post'])
    def cash(self, request, *args, **kwargs):
        serializer = CashSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.select_for_update().get(user=request.user)

        if not wallet.check_password(serializer.validated_data['pay_password']):
            raise ValidationDict211Error('密码错误')

        if not hasattr(wallet, 'bankcard'):
            raise ValidationDict211Error('还没有绑定银行卡')

        if not wallet.bankcard.is_valid:
            raise ValidationDict211Error('银行卡信息有误，请先更正')

        if wallet.remain_cash() < decimal.Decimal(2):
            raise ValidationDict211Error('可提额度不足')

        old_loose_change = wallet.loose_change()
        cash = wallet.cash_out()
        wallet.save(update_fields=['cash'])

        record = CashRecord.objects.create(user=request.user, loose_change=old_loose_change, cash=cash,
            request_bank_name=wallet.bankcard.bank.name, request_acc_name=wallet.bankcard.name,
                                           request_acc_no=wallet.bankcard.card)
        response = PayForAnother(record.number, wallet.bankcard.bank.name, wallet.bankcard.card, wallet.bankcard.name, cash-record.charge)
        response = json.loads(str(response.post(), encoding="utf-8"))

        record.merch_time = timezone.now()
        record.bank_name = wallet.bankcard.bank.name
        record.acc_no = wallet.bankcard.card
        record.acc_name = wallet.bankcard.name
        record.status = 'apply'
        record.handle_time = timezone.now()
        record.retcod = response['RETCOD']
        record.errmsg = response['ERRMSG']
        if record.retcod != 'S':
            record.status = 'fail'
        record.save(update_fields=['merch_time', 'bank_name', 'acc_no', 'acc_name',
                                   'status', 'handle_time', 'retcod', 'errmsg', 'status'])

        return Response({'result': 'OK'})

class BankcardViewSet(viewsets.GenericViewSet):
    queryset = BankCard.objects.all()
    permission_classes = [permissions.IsAuthenticated, HasPayPassword]
    serializer_class = BankcardSerializer

    @list_route(methods=['post'])
    def bind_card(self, request, *args, **kwargs):
        serializer = BindBankcardSerializer(data=request.data)
        serializer.username = request.user.username
        serializer.is_valid(raise_exception=True)

        if not request.user.wallet.check_password(serializer.validated_data['pay_password']):
            raise ValidationDict211Error('密码错误')

        has_card = hasattr(request.user.wallet, 'bankcard')
        if has_card and request.user.wallet.bankcard.is_valid:
            raise ValidationDict211Error('已绑定卡片')

        verify = verify_bankcard(serializer.validated_data['card_name'])
        if not verify[0]:
            raise ValidationDict211Error('银行卡验证失败'+verify[1])

        if not has_card:
            BankCard.objects.create(wallet=request.user.wallet, bank=verify[1], type=verify[2], code=verify[3],
                card=serializer.validated_data['card_name'], name=serializer.validated_data['master_name'],
                phone=serializer.validated_data['phone'])
        else:
            BankCard.objects.filter(wallet=request.user.wallet).update(bank=verify[1], type=verify[2], code=verify[3],
                card=serializer.validated_data['card_name'], name=serializer.validated_data['master_name'],
                phone=serializer.validated_data['phone'], is_valid=True)

        return Response({'result': 'OK'})

    @list_route(methods=['get'])
    def show_card(self, request, *args, **kwargs):
        if not hasattr(request.user.wallet, 'bankcard'):
            raise ValidationDict211Error('未绑定卡片')

        serializer = BankcardSerializer()

        serializer.bank_name = request.user.wallet.bankcard.bank.name
        serializer.ico = request.user.wallet.bankcard.bank.image
        serializer.card_type = request.user.wallet.bankcard.type
        serializer.simple_card = request.user.wallet.bankcard.card[-4:]

        serializer = BankcardSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

    @list_route(methods=['post'])
    def relieve_card(self, request, *args, **kwargs):
        serializer = RelieveBankcardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.wallet.check_password(serializer.validated_data['pay_password']):
            raise ValidationDict211Error('密码错误')

        if not hasattr(request.user.wallet, 'bankcard'):
            raise ValidationDict211Error('未绑定卡片')

        request.user.wallet.bankcard.delete()

        return Response({'result': 'OK'})

class InterfaceViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def mine(self, request, *args, **kwargs):
        user = request.user
        serializer = Interface1Serializer()
        serializer.nick = user.nick_name
        serializer.ico = user.ico_thumbnail
        serializer.describe = user.describe
        serializer.no_disturb = user.myusersettingprofile.no_disturb
        serializer.loose_change = user.wallet.loose_change()
        serializer.have_pay_pw = user.wallet.has_usable_password()
        serializer.have_bankcard = hasattr(user.wallet, 'bankcard') and user.wallet.bankcard.is_valid
        serializer.have_national_id = hasattr(user, 'nationalid') and user.nationalid.is_valid
        serializer.available_tickets = TradeTicketProfile.objects.filter(trade__buyer=user, status='pay').count()

        third_auth = ThirdAuthSerializer()
        if hasattr(user, 'third'):
            third_auth.qq = True if hasattr(user.third, 'qq_unionid') and user.third.qq_unionid else False
            third_auth.weixin = True if hasattr(user.third, 'weixin_unionid') and user.third.weixin_unionid else False
            third_auth.weibo = True if hasattr(user.third, 'weibo_unionid') and user.third.weibo_unionid else False
            third_auth.zhifubao = True if hasattr(user.third, 'zhifubao_unionid') and user.third.zhifubao_unionid else False

        serializer.third_auth = third_auth

        serializer = Interface1Serializer(serializer, context=self.get_serializer_context())
        return Response(serializer.data)

    @list_route(methods=['get'])
    def has_phone(self, request, *args, **kwargs):
        serializer = HasPhoneSerializer()
        if request.user.phone_number:
            serializer.flag = True
            serializer.phone_number = request.user.phone_number
        else:
            serializer.flag = False

        serializer = HasPhoneSerializer(serializer)
        return Response(serializer.data)

    @list_route(methods=['get'])
    def has_pay_pw(self, request, *args, **kwargs):
        return Response({'flag': request.user.wallet.has_usable_password()})

class FriendViewSet(common.views.FriendViewSet):
    @list_route(methods=['get'])
    def new_friend(self, request, *args, **kwargs):
        serializer = SearchFriendSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        search = serializer.validated_data['search']
        queryset = MyUser.objects.filter(~Q(id=request.user.id) & (Q(username=search) | Q(nick_name=search)))[0:10]

        serializer = FriendListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    @detail_route(methods=['get'])
    def detail(self, request, pk=None):
        sql = "SELECT A.nick_name as name, B.alias, A.ico_thumbnail, S.type_id AS major_type, D.name AS group_name " \
            "FROM common_myuser AS A LEFT JOIN common_friend AS B ON A.id = B.friend_id AND B.user_id = %d "\
            "LEFT JOIN common_friendgroup AS D ON D.id = B.group_id " \
            "LEFT JOIN common_myuserspokeprofile AS P ON A.id = P.user_id " \
            "LEFT JOIN common_shop AS S ON P.major_shop_id = S.id " \
            "WHERE A.id = '%s'" \
            % (request.user.id, pk)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializer = None

        for obj in fetchall:
            serializer = FriendDetailSerializer()
            serializer.name = obj[0]
            if obj[1]:
                serializer.alias = obj[1]
            serializer.ico = GetAbsoluteImageUrl(request, obj[2])
            if obj[3]:
                serializer.major_type = obj[3]
            if obj[4]:
                serializer.group_name = obj[4]

            break

        if serializer is None:
            raise ValidationDict211Error('not find')

        sql = "SELECT S.name, S.ico_thumbnail FROM common_shopspoke AS S2 "\
            "LEFT JOIN common_myuser AS U ON S2.spokesman_id = U.id "\
            "LEFT JOIN common_shopmember AS M ON S2.member_id = M.id "\
            "LEFT JOIN common_myuser AS U2 ON M.user_id = U2.id "\
            "LEFT JOIN common_shop AS S ON S2.shop_id = S.id "\
            "WHERE U.id = {0} OR U2.id = {0} ".format(pk)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializer.shops = []
        
        for obj in fetchall:
            shop = FriendSpokesShopSerializer()
            shop.name = obj[0]
            shop.ico = GetAbsoluteImageUrl(request, obj[1])

            serializer.shops.append(shop)

        serializer = FriendDetailSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

    def detail_normal(self, user_id, friend_id):
        sql = "SELECT 'normal', U.id, U.ico, S.id, S.name, S.address, "\
            "S.custom_type, S.`describe`, S.ico_thumbnail, S.`level`, S.type_id, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price, "\
            "G.type, S3.discount FROM common_myuser AS U "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.spokesman_id = U.id "\
            "LEFT JOIN common_shop AS S ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopactivity AS A ON A.shop_id = S.id "\
            "LEFT JOIN common_shopdiscount AS D ON D.shop_id = S.id "\
            "LEFT JOIN common_friend AS F ON F.user_id = U.id AND F.friend_id = {0} "\
            "LEFT JOIN common_friendgroup AS G ON F.group_id = G.id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = G.id AND S3.shop_id = S.id "\
            "WHERE U.id = {1} AND S2.type = 'normal' "\
            .format(user_id, friend_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def detail_member(self, user_id, friend_id):
        sql = "SELECT 'member', U.id, U.ico, S.id, S.name, S.address, "\
            "S.custom_type, S.`describe`, S.ico_thumbnail, S.`level`, S.type_id, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price, " \
            "G.type, S3.member_discount "\
            "FROM common_myuser AS U " \
            "RIGHT JOIN common_shopmember AS M ON M.user_id = U.id " \
            "RIGHT JOIN common_shopspoke AS S2 ON S2.member_id = M.id "\
            "LEFT JOIN common_shop AS S ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopactivity AS A ON A.shop_id = S.id "\
            "LEFT JOIN common_friend AS F ON F.user_id = U.id AND F.friend_id = {0} "\
            "LEFT JOIN common_friendgroup AS G ON F.group_id = G.id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = G.id AND S3.shop_id = S.id, "\
            "common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "WHERE M.shop_id = S.id AND M.user_id = U.id AND M2.id = M.member_card_id "\
            "AND S2.type = 'member' AND M.loose_change > 0 AND U.id = {1} "\
            .format(user_id, friend_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def fill(self, request, obj):
        serializer = FriendSpokesShopDetailSerializer()
        serializer.spokesman_id = obj[1]
        serializer.spokesman_ico = GetAbsoluteImageUrl(request, obj[2])
        serializer.id = obj[3]
        serializer.name = obj[4]
        serializer.address = obj[5]
        if obj[6]:
            serializer.custom_type = obj[6]
        serializer.describe = obj[7]
        serializer.ico = GetAbsoluteImageUrl(request, obj[8])
        serializer.level = obj[9]
        serializer.type = obj[10]

        if obj[11]:
            if 1 == obj[12]:
                serializer.share = '商家活动{0}折'.format(obj[13] / 10)
            elif 2 == obj[12]:
                serializer.share = '商家活动满{0}减{1}元'.format(obj[14], obj[15])

        temp, temp2 = discount_describe_friend(group_type=obj[21], is_valid=obj[16],
            type=obj[17], discount=obj[18], full_price=obj[19], reduce_price=obj[20], friend_discount=obj[22])

        if temp2:
            serializer.discount = temp2

        return serializer

    @detail_route(methods=['get'])
    def detail_more(self, request, pk=None):
        serializers = []

        fetchall = []

        f1 = self.detail_normal(request.user.id, pk)
        f2 = self.detail_member(request.user.id, pk)

        fetchall.extend(list(f1))
        fetchall.extend(list(f2))
        fetchall.sort(key=lambda k: k[1])

        for obj in fetchall:
            serializer = self.fill(request, obj)

            serializers.append(serializer)

        serializer = FriendSpokesShopDetailSerializer(serializers, many=True)
        return Response({'results': serializer.data})

class Flyer2UserViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Flyer2User.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopFlyerSerializer

    def list(self, request, *args, **kwargs):
        serializer = LatitudeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        has_latitude = 'latitude' in serializer.validated_data.keys()
        if has_latitude:
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']

        queryset = Flyer2User.objects.filter(user=request.user, status='valid')

        flyers = []

        for item in queryset:
            if 3 == item.flyer.type:
                item.flyer.ticket_number = item.ticket_number
            item.flyer.distance = calcDistance(item.flyer.shop.latitude, item.flyer.shop.longitude, latitude,
                                         longitude) if has_latitude else None
            flyers.append(item.flyer)

        page = self.paginate_queryset(flyers)

        if page is not None:
            serializer = self.serializer_class(flyers, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(flyers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

class FlyerProfileViewSet(mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, ]

    def retrieve(self, request, *args, **kwargs):
        instance = self.model_class.objects.get(pk=kwargs['pk'])
        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.model_class.objects.get(pk=kwargs['pk'])
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(**serializer.validated_data)

        return Response({'detail': 'OK'})

class FlyerDiscountViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerDiscountProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerDiscountProfileSerializer

    pass

class FlyerReduceViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerReduceProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerReduceProfileSerializer

    pass

class FlyerExperienceViewSet(FlyerProfileViewSet):
    model_class = ShopFlyerExperienceProfile
    queryset = model_class.objects.all()
    serializer_class = ShopFlyerExperienceProfileSerializer

    pass

