import datetime
from django.db import connection
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import F, Q
from rest_framework import parsers, renderers, viewsets, permissions, generics, mixins, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from MyAbstract.exceptions import ValidationDict211Error
from RedisIF.shop import Shop as redis_shop
from common.models import MyUser, Wallet, AdminOperateRecord, TaxMonthRecord, NationalId, Shop, CashRecord, Feedback, \
    RandomNickImage, ShopDiscount, ShopSpoke, ShopSpokeGroup, FriendGroup, ShopPayZSProfile, MarketServer, \
    MarketServerGroup
from common.function import register_profile
from common.serializers import EmptySerializer, UserNationalIdSerializer, JudgeSerializer, ShopBusinessLicenceSerializer
from .serializers import ShopListSerializer, ShopSerializer, ShopJudgeSerializer, PersonCashRecordFilterSerializer, \
    PersonCashRecordSerializer, FeedbackSerializer, UserFilterSerializer, UserSerializer, NationalSerializer, \
    DateFilterSerializer, TradeAmountSerializer, TradeDateSerializer, ShopUserSerializer, ZSShopSerializer, \
    ShopCreateSerializer, MarketServerSerializer, MarketServerManagerCreateSerializer
from .commands import combo_check, ShopSettlement, repair_shop_cash, tax


class AdminViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def tax_month(self, request, *args, **kwargs):
        last = None

        try:
            last = AdminOperateRecord.objects.filter(type='tax', status='success').order_by('-id')[0]
        except:
            pass

        if last and (last.time + relativedelta(months=1)) > timezone.now():
            AdminOperateRecord.objects.create(user=request.user, type='tax', status='refuse')
            return Response('false')

        queryset = Wallet.objects.all()

        for item in queryset:
            ex_remain, income, cash = item.remain, item.income, item.cash
            remain, tax = item.tax_month()
            item.save()
            TaxMonthRecord.objects.create(user=item.user, ex_remain=ex_remain, income=income, cash=cash, tax=tax, remain=remain)

        AdminOperateRecord.objects.create(user=request.user, type='tax', status='success')

        return Response('')

    @list_route(methods=['get'])
    def combo_check(self, request, *args, **kwargs):
        combo_check(user=request.user)

        return Response('')

    @list_route(methods=['get'])
    def shop_settlement(self, request, *args, **kwargs):
        ShopSettlement.shop_settlement(user=request.user, name='shop settle')

        return Response('')

    @list_route(methods=['get'])
    def repair_shop_cash(self, request, *args, **kwargs):
        repair_shop_cash(user=request.user)

        return Response('')

    @list_route(methods=['get'])
    def tax(self, request, *args, **kwargs):
        tax(user=request.user)

        return Response('')

class NationalIdViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = NationalId.objects.filter(~Q(is_valid=True))
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = UserNationalIdSerializer

    @detail_route(methods=['post'])
    def judge(self, request, pk=None):
        serializer = JudgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = serializer.validated_data['judge']

        instance = self.get_object()
        if judge:
            instance.is_valid = True
            instance.save(update_fields=['is_valid'])

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class ShopViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = Shop.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = ShopSerializer

    def list(self, request, *args, **kwargs):
        sql = "SELECT IFNULL(shop_id1, shop_id2) AS shop_id, IFNULL(trade_price1,0) + IFNULL(trade_price2,0) AS trade_price FROM "\
            "(SELECT SUM(B.trade_price) AS trade_price1, A.shop_id AS shop_id1 FROM common_trade AS A LEFT JOIN common_tradediscountprofile AS B ON A.id = B.trade_id "\
            "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' GROUP BY A.shop_id) AS A "\
            "LEFT JOIN "\
            "(SELECT SUM(B.trade_price) AS trade_price2, A.shop_id AS shop_id2 FROM common_trade AS A RIGHT JOIN common_tradeticketprofile AS B ON A.id = B.trade_id "\
            "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' GROUP BY A.shop_id) AS B "\
            "ON A.shop_id1 = B.shop_id2 "\
            "UNION ALL "\
            "SELECT IFNULL(shop_id1, shop_id2) AS shop_id, IFNULL(trade_price1,0) + IFNULL(trade_price2,0) AS trade_price FROM "\
            "(SELECT SUM(B.trade_price) AS trade_price1, A.shop_id AS shop_id1 FROM common_trade AS A LEFT JOIN common_tradediscountprofile AS B ON A.id = B.trade_id "\
            "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' GROUP BY A.shop_id) AS A "\
            "RIGHT JOIN "\
            "(SELECT SUM(B.trade_price) AS trade_price2, A.shop_id AS shop_id2 FROM common_trade AS A RIGHT JOIN common_tradeticketprofile AS B ON A.id = B.trade_id "\
            "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' GROUP BY A.shop_id) AS B "\
            "ON A.shop_id1 = B.shop_id2"

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        queryset = Shop.objects.all()

        for query in queryset:
            for obj in fetchall:
                if query.id == obj[0]:
                    query.sale_month = obj[1]
                    break

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = ShopListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ShopListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @list_route(methods=['get'])
    def list2(self, request, *args, **kwargs):
        serializer = DateFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        begin = serializer.validated_data['begin_time'] if 'begin_time' in serializer.validated_data.keys() else datetime.datetime.now().date()
        end = serializer.validated_data['end_time'] if 'end_time' in serializer.validated_data.keys() else datetime.datetime.now()

        sql = "SELECT T.shop_id, S.name, SUM(T.count), SUM(T.sum) FROM "\
            "(SELECT T.shop_id, COUNT(T.shop_id) AS count, SUM(T.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradediscountprofile AS TD ON T.id = TD.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TD.`status` in ('pay', 'confirm') "\
            "AND date_add(T.trade_time, interval 8 hour) BETWEEN '{0}' AND '{1}' "\
            "GROUP BY T.shop_id "\
            "UNION ALL "\
            "SELECT T.shop_id, COUNT(T.shop_id) AS count, SUM(TT.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradeticketprofile AS TT ON T.id = TT.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TT.`status` in ('confirm') "\
            "AND date_add(TT.confirm_time, interval 8 hour) BETWEEN '{0}' AND '{1}' "\
            "GROUP BY T.shop_id "\
            "UNION ALL "\
            "SELECT T.shop_id, COUNT(T.shop_id) AS count, SUM(T.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradememberprofile AS TM ON T.id = TM.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TM.`status` in ('pay') "\
            "AND date_add(T.trade_time, interval 8 hour) BETWEEN '{0}' AND '{1}' "\
            "GROUP BY T.shop_id) AS T "\
            "LEFT JOIN common_shop AS S ON T.shop_id = S.id "\
            "GROUP BY T.shop_id "\
            "ORDER BY T.shop_id ".format(begin, end)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for obj in fetchall:
            serializer = TradeAmountSerializer()
            serializer.shop_id = obj[0]
            serializer.name = obj[1]
            serializer.count = obj[2]
            serializer.sum = obj[3]

            serializers.append(serializer)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = TradeAmountSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = TradeAmountSerializer(serializers, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = ShopCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.request = request
        serializer.save()

        return Response({'detail': 'OK'})

    @list_route(methods=['get'])
    def wait_for(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.queryset.filter(Q(state=1)|Q(state=2)))

        if page is not None:
            serializer = ShopListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = ShopListSerializer(self.queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['get'])
    def detail(self, request, pk=None):
        serializer = DateFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        begin = serializer.validated_data['begin_time'] if 'begin_time' in serializer.validated_data.keys() else datetime.datetime.now().date()
        end = serializer.validated_data['end_time'] if 'end_time' in serializer.validated_data.keys() else datetime.datetime.now()

        sql = "SELECT T.date, SUM(T.count), SUM(T.sum) FROM "\
            "(SELECT DATE_FORMAT(date_add(T.trade_time, interval 8 hour),'%Y%m%d') AS date, " \
            "COUNT(T.shop_id) AS count, SUM(T.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradediscountprofile AS TD ON T.id = TD.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TD.`status` in ('pay', 'confirm') "\
            "AND shop_id = {0} AND date_add(T.trade_time, interval 8 hour) BETWEEN '{1}' AND '{2}' "\
            "GROUP BY DATE_FORMAT(date_add(T.trade_time, interval 8 hour),'%Y%m%d') "\
            "UNION ALL "\
            "SELECT DATE_FORMAT(date_add(TT.confirm_time, interval 8 hour),'%Y%m%d') AS date, " \
            "COUNT(T.shop_id) AS count, SUM(TT.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradeticketprofile AS TT ON T.id = TT.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TT.`status` in ('confirm') "\
            "AND T.shop_id = {0} AND date_add(T.trade_time, interval 8 hour) BETWEEN '{1}' AND '{2}' "\
            "GROUP BY DATE_FORMAT(date_add(TT.confirm_time, interval 8 hour),'%Y%m%d') "\
            "UNION ALL "\
            "SELECT DATE_FORMAT(date_add(T.trade_time, interval 8 hour),'%Y%m%d') AS date, " \
            "COUNT(T.shop_id) AS count, SUM(T.trade_price) AS sum FROM common_trade AS T "\
            "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id "\
            "RIGHT JOIN common_tradememberprofile AS TM ON T.id = TM.trade_id "\
            "WHERE T.has_pay = TRUE AND TP.is_seller IS FALSE AND TP.pay_type not in ('member') AND TM.`status` in ('pay') "\
            "AND T.shop_id = {0} AND date_add(T.trade_time, interval 8 hour) BETWEEN '{1}' AND '{2}' "\
            "GROUP BY DATE_FORMAT(date_add(T.trade_time, interval 8 hour),'%Y%m%d')) AS T "\
            "GROUP BY T.date "\
            "ORDER BY T.date ".format(pk, begin, end)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        serializers = []

        for obj in fetchall:
            serializer = TradeDateSerializer()
            serializer.date = obj[0]
            serializer.count = obj[1]
            serializer.sum = obj[2]

            serializers.append(serializer)

        page = self.paginate_queryset(serializers)

        if page is not None:
            serializer = TradeDateSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = TradeDateSerializer(serializers, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def judge(self, request, pk=None):
        serializer = ShopJudgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = serializer.validated_data['judge']

        instance = self.get_object()
        if judge:
            instance.state = 4
            instance.staff_name = serializer.validated_data['staff']
            instance.save(update_fields=['state', 'staff_name'])

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['patch'])
    def business_licence(self, request, pk=None):
        instance = self.get_object()
        serializer = ShopBusinessLicenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.update(instance, serializer.validated_data)

        return Response('')

    @detail_route(methods=['post'])
    def modify_user(self, request, pk=None):
        serializer = ShopUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        type = serializer.validated_data['type']

        try:
            user = MyUser.objects.get(username=username)
        except MyUser.DoesNotExist:
            temp = RandomNickImage.objects.all().order_by('?')[0]
            data = {}
            data['phone_number'] = username
            data['nick_name'] = temp.nick
            data['ico'] = temp.image
            user = MyUser(**data)
            user.set_unusable_password()
            user.save()
            register_profile(request, user)

        # todo
        ShopSpoke.objects.create(shop_id=pk, spokesman=user, type='normal')
        shop_discount = ShopDiscount.objects.get(pk=pk)
        discount = 0.5 * shop_discount.discount + 50 if 1 == shop_discount.type else 0.5 * shop_discount.reduce_price
        ShopSpokeGroup.objects.create(shop_id=pk, group=FriendGroup.objects.get(user=user, type=3), discount=discount)
        data2 = {}
        data2['spoke_count'] = F('spoke_count')+1
        if 1 == type & 1:
            data2['seller'] = user
        if 2 == type & 2:
            data2['manager'] = user

        Shop.objects.filter(pk=pk).update(**data2)

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    def zs_shop(self, request, pk=None):
        serializer = ZSShopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ShopPayZSProfile.objects.filter(shop_id=pk).update(open_id=serializer.validated_data['open_id'],
            open_key=serializer.validated_data['open_key'], type='shop')
        if serializer.validated_data['is_zs_card']:
            Shop.objects.filter(id=pk).update(brokerage_type=2, charge_ratio=30)
            redis_shop.set_charge_ratio(pk, 30)
        else:
            Shop.objects.filter(id=pk).update(brokerage_type=2)

        return Response({'result': 'OK'})

class PersionCashViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = CashRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = PersonCashRecordSerializer

    def list(self, request, *args, **kwargs):
        serializer = PersonCashRecordFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter = None
        if 'username' in serializer.validated_data.keys():
            q = Q(user__username=serializer.validated_data['username'])
            filter = filter & q if filter else q
        if 'status' in serializer.validated_data.keys():
            q = Q(status=serializer.validated_data['status'])
            filter = filter & q if filter else q
        if 'begin_time' in serializer.validated_data.keys():
            q = Q(request_time__gte=serializer.validated_data['begin_time'])
            filter = filter & q if filter else q
        if 'end_time' in serializer.validated_data.keys():
            q = Q(request_time__lt=serializer.validated_data['end_time'])
            filter = filter & q if filter else q

        if filter:
            queryset = CashRecord.objects.filter(filter).order_by('-id')
        else:
            queryset = CashRecord.objects.all().order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

class FeedbackViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Feedback.objects.all().order_by('-id')
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = FeedbackSerializer

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(self.queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

class UserViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = UserSerializer

    def list(self, request, *args, **kwargs):
        serializer = UserFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        filter = None
        if 'username' in serializer.validated_data.keys():
            q = Q(username=serializer.validated_data['username'])
            filter = filter & q if filter else q

        if filter:
            queryset = MyUser.objects.filter(filter).order_by('-id')
        else:
            queryset = MyUser.objects.all().order_by('-id')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.serializer_class(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @detail_route(methods=['get', 'post'])
    def national(self, request, pk=None):
        if request.method == 'GET':
            try:
                national = NationalId.objects.get(user_id=pk)
            except:
                raise ValidationDict211Error('没有实名制')

            serializer = NationalSerializer(national, context=self.get_serializer_context())

            return Response(serializer.data)
        elif request.method == 'POST':
            try:
                nationalid = NationalId.objects.get(pk=pk)
                serializer = NationalSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)

                serializer.update(nationalid, serializer.validated_data)
            except NationalId.DoesNotExist:
                serializer = NationalSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.validated_data['user_id'] = pk
                serializer.validated_data['is_valid'] = True

                serializer.save(**serializer.validated_data)

            return Response('')

    @detail_route(methods=['post'])
    def modify_pw(self, request, pk=None):
        user = MyUser.objects.get(pk=pk)
        user.set_password('123456')
        user.save(update_fields=['password'])

        return Response('')

class MarketServerViewSet(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = MarketServer.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = MarketServerSerializer

    @detail_route(methods=['post'])
    def manager(self, request, pk):
        serializer = MarketServerManagerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = MarketServerGroup.objects.filter(server_id=pk, level=0)[0]
        serializer.save(group_id=group.id)
        return Response({'detail': 'OK'})

class MarketServerGroupViewSet(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = MarketServer.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = MarketServerSerializer
