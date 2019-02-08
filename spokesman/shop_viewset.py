from urllib.parse import quote

from django.db import connection, IntegrityError
from django.db.models import F, Q
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
import random, decimal
from APNS import apns, apns_seller, apns_push
from Logger.logger import Logger
from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl, decimal2string, calcDistance
from common.models import create_trade_number, MyUser,  Shop, SpokesmanResume, ShopSpokeRequest, ShopSpoke, CollectShop, ShopLicence, Trade, \
    ShopRequire, ShopCombo, TradeDiscountProfile, ShopMemberCard, ShopMember, Wallet, ShopActivity, ShopDiscount, \
    ShopFlyer, ShopFlyerDiscountProfile, ShopFlyerReduceProfile, ShopFlyerExperienceProfile, ShopFlyerExperienceGoods, \
    Flyer2Shop, Flyer2User
from common.function import spoker_type, discount_describe_friend
import common.views
from .function import calculate_trade_dict, calculate
from .serializers import ShopSerializer, ShopRetrieveSerializer, CollectShopSerializer, ShopBusinessLicencesSerializer, ShopLicencesSerializer, \
    CompleteTradeSerializer, ShopWithSpokesSerializer, ShopRequireSerializer, \
    ShopShareUrlSerializer, ShopSimpleSerializer, TradeCalculateSerializer, ShopRequire2Serializer, TradeResponseSerializer, \
    ShopMemberInfoSerializer, ShopFlyerSerializer, ShopFlyerProfileMineSerializer, ShopBuyParaSerializer, ShopInfo1Serializer, \
    TradeGetFlyerSerializer
from .shop_discount import ShopDiscountCalculate


class ShopViewSet(common.views.ShopViewSet):
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopSerializer

    def retrieve(self, request, *args, **kwargs):
        shop_with_spokes = ShopWithSpokesSerializer(data=request.query_params)
        shop_with_spokes.is_valid(raise_exception=True)

        instance = self.get_object()

        serializer = ShopRetrieveSerializer()
        serializer.id = instance.id
        serializer.name = instance.name
        serializer.address = instance.address
        serializer.phone = instance.phone
        serializer.latitude = instance.latitude
        serializer.longitude = instance.longitude
        serializer.ico = instance.ico_thumbnail
        serializer.face = instance.face
        serializer.level = instance.level
        serializer.photos = instance.photos.all()[0:4]

        serializer.describe = instance.describe
        serializer.open_time = instance.open_time
        serializer.close_time = instance.close_time
        serializer.convenience = instance.convenience
        serializer.announcement = instance.announcement

        spokesman_id = None
        spoke_type = None
        if 'spokesman_id' in shop_with_spokes.validated_data.keys():
            spoke_type = spoker_type(instance.id, shop_with_spokes.validated_data['spokesman_id'])
            if spoke_type:
                spokesman_id = shop_with_spokes.validated_data['spokesman_id']

        self.spokesman, self.discount = ShopDiscountCalculate().calculate(request, instance.id, spokesman_id, spoke_type)

        serializer.spokesman_id = self.spokesman['id']
        serializer.spokesman_im_id = self.spokesman['id']
        serializer.spokesman_name = self.spokesman['nick']
        serializer.spokesman_ico = GetAbsoluteImageUrl(request, self.spokesman['ico_thumbnail'])

        if serializer.spokesman_id == instance.seller_id:
            serializer.spokesman_describe = '商家'
        else:
            serializer.spokesman_describe = '好友'

        serializer.activity_is_valid = instance.activity.is_valid
        if serializer.activity_is_valid:
            serializer.activity_type = instance.activity.type
            serializer.activity = instance.activity
            if 1 == serializer.activity_type:
                serializer.activity_discount = instance.activity.discount
            elif 2 == serializer.activity_type:
                serializer.activity_full_price = instance.activity.full_price
                serializer.activity_reduce_price = instance.activity.reduce_price

        serializer.discount_is_valid = 'is_valid' in self.discount.keys() and self.discount['is_valid']
        if serializer.discount_is_valid:
            serializer.discount_type = self.discount['type']
            serializer.discount = self.spokesman['discount']
            if 1 == serializer.discount_type:
                serializer.discount_discount = self.discount['discount']
            elif 2 == serializer.discount_type:
                serializer.discount_full_price = self.discount['full_price']
                serializer.discount_reduce_price = self.discount['reduce_price']

        serializer.combo = ShopCombo.objects.filter(shop=instance, status='online')
        serializer.comment_count = instance.comment_count
        serializer.is_collect = CollectShop.objects.filter(user=request.user, shop=instance).exists()
        serializer.is_spokes = ShopSpoke.objects.filter(Q(shop=instance) & (Q(spokesman=request.user) | Q(member__user=request.user))).exists()
        serializer.has_member = ShopMemberCard.objects.filter(shop=instance, status='valid').exists()
        if serializer.has_member:
            serializer.is_member = ShopMember.objects.filter(shop=instance, user=request.user).exists()

        serializer = ShopRetrieveSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['get'])
    def info1(self, request, pk=None):
        serializer = ShopInfo1Serializer(Shop.objects.get(pk=pk), context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['get'])
    def simple(self, request, pk=None):
        shop_with_spokes = ShopWithSpokesSerializer(data=request.query_params)
        shop_with_spokes.is_valid(raise_exception=True)

        instance = self.get_object()

        serializer = ShopSimpleSerializer()

        try:
            if instance.activity and instance.activity.is_valid:
                serializer.activity = instance.activity
        except:
            pass

        spokesman_id = None
        spoke_type = None
        if 'spokesman_id' in shop_with_spokes.validated_data.keys():
            spoke_type = spoker_type(instance.id, shop_with_spokes.validated_data['spokesman_id'])
            if spoke_type:
                spokesman_id = shop_with_spokes.validated_data['spokesman_id']

        self.spokesman, self.discount = ShopDiscountCalculate().calculate(request, instance.id, spokesman_id, spoke_type)

        if self.spokesman['discount']:
            serializer.discount = self.spokesman['discount']

        serializer.spokesman_id = self.spokesman['id']
        serializer.spokesman_ico = GetAbsoluteImageUrl(request, self.spokesman['ico_thumbnail'])

        serializer = ShopSimpleSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['get'])
    def buy_para(self, request, pk=None):
        shop_with_spokes = ShopWithSpokesSerializer(data=request.query_params)
        shop_with_spokes.is_valid(raise_exception=True)

        instance = self.get_object()
        serializer = ShopBuyParaSerializer()

        serializer.name = instance.name

        try:
            if instance.activity and instance.activity.is_valid:
                serializer.activity = instance.activity
        except:
            pass

        spokesman_id = None
        type = None
        if 'spokesman_id' in shop_with_spokes.validated_data.keys():
            type = spoker_type(instance.id, shop_with_spokes.validated_data['spokesman_id'])
            if type:
                spokesman_id = shop_with_spokes.validated_data['spokesman_id']

        self.spokesman, self.discount = ShopDiscountCalculate().calculate(request, instance.id, spokesman_id, type)

        serializer.shop_ico = instance.ico_thumbnail

        if self.spokesman['discount']:
            serializer.discount = self.spokesman['discount']

        serializer.spokesman_id = self.spokesman['id']
        serializer.spokesman_ico = GetAbsoluteImageUrl(request, self.spokesman['ico_thumbnail'])

        if ShopMemberCard.objects.filter(shop_id=pk).exists():
            try:
                member = ShopMember.objects.get(shop_id=pk, user=request.user)
                serializer.loose_change = decimal2string(member.loose_change)
                serializer.is_member = True
                serializer.has_trade_password = Wallet.objects.get(user=request.user).password
            except ShopMember.DoesNotExist:
                serializer.is_member = False
        else:
            serializer.is_member = False

        flyers = []
        if not serializer.is_member:
            queryset = Flyer2User.objects.filter(user=request.user, flyer__shop_id=pk, status='valid',
                                                 flyer__type__in=(1, 2))

            for item in queryset:
                temp = ShopFlyerProfileMineSerializer()
                temp.ticket_number = item.ticket_number
                temp.type = item.flyer.type
                if 1 == temp.type:
                    temp.discount = item.flyer.discount.discount
                    temp.describe = '店内消费{0}折'.format(temp.discount / 10)
                elif 2 == temp.type:
                    temp.full_price = item.flyer.reduce.full_price
                    temp.reduce_price = item.flyer.reduce.reduce_price
                    temp.describe = '店内消费满{0}减{1}'.format(temp.full_price, temp.reduce_price)

                flyers.append(temp)

        serializer.flyers = flyers

        serializer = ShopBuyParaSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['get'])
    def require(self, request, pk=None):
        query = ShopRequire.objects.get(shop_id=pk)
        serializer = ShopRequireSerializer(query)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def member_info(self, request, pk):
        serializer = ShopMemberInfoSerializer()
        serializer.shop_name = Shop.objects.get(pk=pk).name
        serializer.has_member = ShopMemberCard.objects.filter(shop_id=pk).exists()

        if serializer.has_member:
            try:
                member = ShopMember.objects.get(shop_id=pk, user=request.user)
                serializer.loose_change = member.loose_change
                serializer.is_member = True
                serializer.has_trade_password = Wallet.objects.get(user=request.user).password
            except ShopMember.DoesNotExist:
                serializer.is_member = False

            serializer.image = GetAbsoluteImageUrl(request, ShopMemberCard.objects.filter(shop_id=pk)[0].image)

        serializer = ShopMemberInfoSerializer(serializer)
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def require2(self, request, pk=None):
        query = Shop.objects.get(pk=pk)
        serializer = ShopRequire2Serializer(query, context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def spokes(self, request, pk=None):
        shop = Shop.objects.get(pk=pk)
        if ShopSpoke.objects.filter(Q(shop=shop) & (Q(spokesman=request.user) | Q(member__user=request.user))).exists():
            raise ValidationDict211Error("已是本店代言人", detail_en='had spoked')

        try:
            obj = SpokesmanResume.objects.get(user=request.user)
        except SpokesmanResume.DoesNotExist:
            obj = SpokesmanResume.objects.create(user=request.user, resume='')
            #raise ValidationDict211Error("该用户没有简历信息", detail_en='no resume')

        try:
            ShopSpokeRequest.objects.create(request='request', shop=shop, resume=obj)
            apns_seller.publish_request_spokesman(shop)
        except IntegrityError:
            raise ValidationDict211Error("申请已存在", detail_en='request has existed')

        apns.record_request_spokesman(request.user, request.user.nick_name, shop.name)

        return Response({'result': 'OK'}, status=status.HTTP_201_CREATED)

    @detail_route(methods=['post'])
    def collect(self, request, pk=None):
        serializer = CollectShopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['is_collect']:
            try:
                CollectShop.objects.create(user=request.user, shop_id=pk)
            except:
                raise ValidationDict211Error('已收藏')
        else:
            try:
                CollectShop.objects.get(user=request.user, shop_id=pk).delete()
            except CollectShop.DoesNotExist:
                raise ValidationDict211Error('未收藏')

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @detail_route(methods=['get'])
    def business_licences(self, request, pk=None):
        shop = Shop.objects.get(pk=pk)
        serializer = ShopBusinessLicencesSerializer()
        serializer.business_licence = shop.business_licence.business_licence

        serializer = ShopBusinessLicencesSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @detail_route(methods=['get'])
    def licences(self, request, pk=None):
        shop = Shop.objects.get(pk=pk)
        serializer = ShopLicencesSerializer()
        items = []
        licences = ShopLicence.objects.filter(shop=shop)
        for item in licences:
            items.append(GetAbsoluteImageUrl(request, item.licence))
        serializer.licences = items

        serializer = ShopLicencesSerializer(serializer, context=self.get_serializer_context())

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @detail_route(methods=['get'])
    def random_spokesman(self, request, pk=None):
        #redefine
        sql = "SELECT U.id, U.nick_name, U.ico_thumbnail, " \
              "NULL AS discount " \
              "FROM common_shop AS S " \
              "LEFT JOIN common_myuser AS U ON U.id = S.seller_id " \
              "WHERE S.id = {0}".format(int(pk))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        for obj in fetchall:
            return Response({'id': obj[0], 'ico': GetAbsoluteImageUrl(request, obj[1])})

        raise ValidationDict211Error('no spokesman')

    @detail_route(methods=['post'])
    def share_url(self, request, pk=None):
        serializer = ShopShareUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        temp = 'http://www.dailibuluo.com/WeixinDevelop/shop?action=share&id=%d&spokesman_id=%d' \
               % (int(pk), serializer.validated_data['spokesman_id'])

        url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx3e305e5a9bdc6ba6' \
              '&redirect_uri=%s&response_type=code&scope=snsapi_userinfo&state=STATE#wechat_redirect' % quote(temp)

        return Response({'url': url})

    def fill_discount_dict(self, valid, type=1, discount=100, full_price=100, reduce_price=0, spoke=None):
        self.discount['is_valid'] = valid
        self.discount['type'] = type
        self.discount['discount'] = discount
        self.discount['full_price'] = full_price
        self.discount['reduce_price'] = reduce_price
        self.discount['spoke'] = spoke

    def mine_normal(self, shop_id, user_id):
        sql = "SELECT 'normal', "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price "\
            "FROM common_shop AS S, common_shopdiscount AS D, common_shopspoke AS S2, common_myuser AS U "\
            "WHERE D.shop_id = S.id AND S2.shop_id = S.id AND S2.spokesman_id = U.id AND S2.type = 'normal' " \
            "AND U.id = {0} AND S.id = {1}".format(user_id, shop_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def mine_member(self, shop_id, user_id):
        sql = "SELECT 'member', CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price "\
            "FROM common_shop AS S, common_shopmember AS M, common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id, "\
            "common_shopspoke AS S2, common_myuser AS U "\
            "WHERE M.shop_id = S.id AND M.user_id = U.id AND M2.id = M.member_card_id "\
            "AND U.id = M.user_id AND S2.shop_id = S.id AND S2.member_id = M.id AND M.user_id = U.id " \
            "AND S2.type = 'member' AND M.loose_change > 0 "\
            "AND U.id = {0} AND S.id = {1}".format(user_id, shop_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def mine(self, shop_id, user_id, type):
        if 'member' == type:
            fetchall = self.mine_member(shop_id, user_id)
        else:
            fetchall = self.mine_normal(shop_id, user_id)

        for obj in fetchall:
            if 'member' == obj[0]:
                self.fill_discount_dict(bool(obj[1]), obj[2], obj[3], obj[4], obj[5], spoke=obj[3] if 1 == obj[2] else obj[5])
            else:
                self.fill_discount_dict(obj[1], obj[2], obj[3], obj[4], obj[5], spoke=obj[3] if 1 == obj[2] else obj[5])

            return True

        return False

    def friend_normal(self, shop_id, user_id, spoker_id):
        sql = "SELECT 'normal', "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price, "\
            "G.type, S3.discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = S2.spokesman_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = F.group_id AND S3.shop_id = S.id, "\
            "common_friendgroup AS G, common_myuser AS U, common_shopdiscount AS D "\
            "WHERE S.id = {0} AND F.friend_id = {1} AND U.id = {2} AND G.id = F.group_id AND F.user_id = U.id " \
            "AND S.id = D.shop_id AND S2.type = 'normal' "\
            .format(shop_id, user_id, spoker_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def friend_member(self, shop_id, user_id, spoker_id):
        sql = "SELECT 'member', CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price, " \
            "G.type, S3.member_discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopmember AS M ON M.id = S2.member_id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = M.user_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = F.group_id AND S3.shop_id = S.id, "\
            "common_friendgroup AS G, common_myuser AS U, "\
            "common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "WHERE S.id = {0} AND F.friend_id = {1} AND U.id = {2} AND G.id = F.group_id AND F.user_id = U.id "\
            "AND M.shop_id = S.id AND M.user_id = U.id AND M2.id = M.member_card_id "\
            "AND S2.type = 'member' AND M.loose_change > 0 "\
            .format(shop_id, user_id, spoker_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def friend(self, shop_id, user_id, spoker_id, type):
        if 'member' == type:
            fetchall = self.friend_member(shop_id, user_id, spoker_id)
        else:
            fetchall = self.friend_normal(shop_id, user_id, spoker_id)

        for obj in fetchall:
            if 'member' == obj[0]:
                discount_discount, spoker_discount = discount_describe_friend(group_type=obj[6], is_valid=bool(obj[1]),
                    type=obj[2], discount=obj[3], full_price=obj[4], reduce_price=obj[5], friend_discount=obj[7])
                self.fill_discount_dict(bool(discount_discount), obj[2], obj[3], obj[4], obj[5], discount_discount)
            else:
                discount_discount, spoker_discount = discount_describe_friend(group_type=obj[6], is_valid=obj[1],
                    type=obj[2], discount=obj[3], full_price=obj[4], reduce_price=obj[5], friend_discount=obj[7])
                self.fill_discount_dict(bool(discount_discount), obj[2], obj[3], obj[4], obj[5], discount_discount)

            return True

        return False

    def other(self, shop_id, user_id, type):
        if 'member' == type:
            card = ShopMemberCard.objects.get(shop=shop_id, member__user_id=user_id)
            discount = card.discount if hasattr(card, 'discount') else None
            self.fill_discount_dict(bool(discount), discount.type, discount.discount, discount.full_price,
                                    discount.reduce_price)
        else:
            discount = ShopDiscount.objects.get(pk=shop_id)
            self.fill_discount_dict(discount.is_valid, discount.type, discount.discount, discount.full_price,
                                    discount.reduce_price)

    def __trade_dict(self, shop_id, user_id, spoker_id, spoke_type, total, constant):
        self.discount = {}

        if user_id == spoker_id:
            if not self.mine(shop_id, user_id, spoke_type):
                raise ValidationDict211Error('error', detail_en='error')
        elif self.friend(shop_id, user_id, spoker_id, spoke_type):
            pass
        else:
            self.other(shop_id, spoker_id, spoke_type)

        activity = ShopActivity.objects.get(pk=shop_id)
        is_manager = Shop.objects.filter(pk=shop_id, managers=spoker_id).exists()

        trade_dict = calculate_trade_dict(total, constant, activity.is_valid, activity.type, activity.discount,
            activity.full_price, activity.reduce_price, self.discount['is_valid'], self.discount['type'],
            self.discount['discount'], self.discount['full_price'], self.discount['reduce_price'],
            self.discount['spoke'], is_manager)

        return trade_dict

    def __trade_dict_ticket(self, shop_id, flyer2user, total, constant):
        flyer = flyer2user.flyer
        self.discount = {'is_valid':True, 'type':flyer.type}

        if 1 == flyer.type:
            self.discount['spoke'] = self.discount['discount'] = flyer.discount.discount
            self.discount['full_price'] = 100
            self.discount['reduce_price'] = 0
        elif 2 == flyer.type:
            self.discount['full_price'] = flyer.reduce.full_price
            self.discount['spoke'] = self.discount['reduce_price'] = flyer.reduce.reduce_price
            self.discount['discount'] = 100
        else:
            raise ValidationDict211Error('error')

        trade_dict = calculate_trade_dict(total, constant, False, None, None, None, None,
            self.discount['is_valid'], self.discount['type'],
            self.discount['discount'], self.discount['full_price'], self.discount['reduce_price'],
            self.discount['spoke'], True)

        return trade_dict

    @detail_route(methods=['post'])
    def calculate(self, request, pk=None):
        serializer = CompleteTradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        total = serializer.validated_data['discount_price']
        constant = serializer.validated_data['constant_price'] if 'constant_price' in serializer.validated_data.keys() else 0

        if 'ticket_number' in serializer.validated_data:
            ticket_number = serializer.validated_data['ticket_number']
            flyer2user = Flyer2User.objects.get(ticket_number=ticket_number)
            trade_dict = self.__trade_dict_ticket(pk, flyer2user, total, constant)
        else:
            spoke_type = spoker_type(pk, serializer.validated_data['spokesman'])
            if spoke_type:
                spoker_id = serializer.validated_data['spokesman']
            else:
                raise ValidationDict211Error('代言人不存在', detail_en='the man is fake')

            trade_dict = self.__trade_dict(pk, request.user.id, spoker_id, spoke_type, total, constant)

        serializer = TradeCalculateSerializer(trade_dict)

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def trade(self, request, pk=None):
        serializer = CompleteTradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trade = self.__trade(request, pk, serializer)

        serializer = TradeResponseSerializer({'id': trade.trade_number, 'price': trade.trade_price,
            'ico': GetAbsoluteImageUrl(request, trade.shop.ico_thumbnail)})

        return Response(serializer.data)

    def __trade(self, request, pk, serializer):
        total = serializer.validated_data['discount_price']
        constant = serializer.validated_data['constant_price'] if 'constant_price' in serializer.validated_data.keys() else 0

        ticket = None

        if 'ticket_number' in serializer.validated_data:
            ticket_number = serializer.validated_data['ticket_number']
            ticket = Flyer2User.objects.get(ticket_number=ticket_number)
            trade_dict = self.__trade_dict_ticket(pk, ticket, total, constant)
            spoker_id = Shop.objects.get(pk=pk).seller_id
            ticket.status = 'used'
            ticket.save(update_fields=['status'])
        else:
            spoke_type = spoker_type(pk, serializer.validated_data['spokesman'])
            if spoke_type:
                spoker_id = serializer.validated_data['spokesman']
            else:
                raise ValidationDict211Error('代言人不存在', detail_en='the man is fake')

            self.client_price = serializer.validated_data['client_price'] \
                if hasattr(serializer.validated_data, 'client_price') else None

            trade_dict = self.__trade_dict(pk, request.user.id, spoker_id, spoke_type, total, constant)

        trade = self.create_trade(pk, request.user.id, spoker_id, total, constant, trade_dict, ticket)

        return trade

    def create_trade(self, shop_id, buyer_id, spoker_id, total, constant, trade_dict, ticket=None):
        trade = Trade.objects.create(profile_type='discount', shop_id=shop_id, buyer_id=buyer_id, spokesman_id=spoker_id,
            shop_discount=trade_dict['shop_discount'] if trade_dict['is_discount'] else None,
            discount=trade_dict['spokesman_discount'] if trade_dict['is_discount'] else None,
            total_fee=total, trade_price=trade_dict['trade_price'])

        profile = TradeDiscountProfile.objects.create(trade=trade, trade_price=trade_dict['trade_price'],
            activity=trade_dict['activity'], discount_price=total - constant,
            constant_price=constant, activity_reduce=trade_dict['activity_reduce'],
            discount_reduce=trade_dict['discount_reduce'], brokerage_design=trade_dict['brokerage'], ticket=ticket)

        trade.tradediscountprofile = profile

        #if self.client_price and self.client_price != trade.trade_price:
        #    Logger.Log('warning', 'trade price {0} {1} {2}'.format(trade.id, trade.trade_price, self.client_price))

        return trade

    @detail_route(methods=['post'])
    def ticket(self, request, pk=None):
        serializer = TradeGetFlyerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trade_number = serializer.validated_data[
            'trade_number'] if 'trade_number' in serializer.validated_data.keys() else None
        has_latitude = 'latitude' in serializer.validated_data.keys()
        if has_latitude:
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']

        sql = "SELECT FS.flyer_id, F.shop_id FROM common_flyer2shop as FS "\
                "LEFT JOIN common_shopflyer AS F ON FS.flyer_id = F.id "\
                "WHERE FS.shop_id = {0}".format(pk)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        flyer_ids = []
        shop_ids = set()

        if 0 == len(fetchall):
            return Response({'results': []})

        for obj in fetchall:
            flyer_ids.append(obj[0])
            shop_ids.add(obj[1])

        sql = "SELECT FU.flyer_id FROM common_flyer2user AS FU " \
              "LEFT JOIN common_shopflyer AS F ON FU.flyer_id = F.id " \
              "WHERE FU.user_id = {0} AND (FU.flyer_id in ({1}) " \
              "OR (FU.status = 'valid' AND F.shop_id in ({2})))" \
              .format(request.user.id, ','.join(str(e) for e in flyer_ids), ','.join(str(e) for e in shop_ids))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        temp = []
        temp2 = []
        for item in flyer_ids:
            if item not in [obj[0] for obj in fetchall]:
                temp.append(item)
            else:
                temp2.append(item)

        print('test1', len(temp), len(temp2))

        flyer_ids = temp + temp2

        #flyer_ids = [item for item in flyer_ids if item not in [obj[0] for obj in fetchall]]

        length = len(flyer_ids)
        if 0 == length:
            return Response({'results':[]})

        trade = Trade.objects.get(trade_number=trade_number) if trade_number else None

        flyers = ShopFlyer.objects.filter(pk__in=flyer_ids, status='online')[:2]

        #Flyer2User.objects.bulk_create([Flyer2User(user=request.user, shop_id=pk, flyer=item) for item in flyers])
        for item in flyers:
            if item.id in temp:
                item.is_new = True
                Flyer2User.objects.create(user=request.user, shop_id=pk, flyer=item, trade=trade)
                Flyer2Shop.objects.filter(shop_id=pk, flyer=item).update(count=F('count') + 1)
            else:
                item.is_new = False

            item.distance = calcDistance(item.shop.latitude, item.shop.longitude, latitude, longitude) if has_latitude else None

        serializer = ShopFlyerSerializer(flyers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    @detail_route(methods=['get'])
    def my_flyer(self, request, *args, **kwargs):
        queryset = Flyer2User.objects.filter(user=request.user, flyer__shop_id=kwargs['pk'], status='valid',
                                             flyer__type__in=(1, 2))

        serializers = []

        for item in queryset:
            temp = ShopFlyerProfileMineSerializer()
            temp.ticket_number = item.ticket_number
            temp.type = item.flyer.type
            if 1 == temp.type:
                temp.discount = item.flyer.discount.discount
                temp.describe = '店内消费{0}折'.format(temp.discount / 10)
            elif 2 == temp.type:
                temp.full_price = item.flyer.reduce.full_price
                temp.reduce_price = item.flyer.reduce.reduce_price
                temp.describe = '店内消费满{0}减{1}'.format(temp.full_price, temp.reduce_price)

            serializers.append(temp)

        serializer = ShopFlyerProfileMineSerializer(serializers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})
