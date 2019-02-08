from random import randint

from django.db import connection
from django.db.models import Q
from rest_framework import viewsets, permissions, mixins
from rest_framework.response import Response
from SpokesTribe.settings import BROTHER_RATIO1, BROTHER_RATIO2
from MyAbstract.exceptions import ValidationDict211Error
from RedisIF.RedisIF import RedisIF
from MyAbstract.funtions import GetAbsoluteImageUrl, calcDistance, calcDistance
from common.models import Shop, ShopCombo
from common.function import discount_describe_mine, discount_describe_friend
from .function import calculate
from .serializers import FindShopResponseSerializer, FindShopSerializer
from MyAbstract.funtions import fenceil, fenfloor


class FindShopViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Shop.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = FindShopResponseSerializer

    def list(self, request, *args, **kwargs):
        serializer = FindShopSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        shop_type = None
        self.queryset = []

        if 'shop_type' in serializer.data:
            shop_type = serializer.data['shop_type']

        self.around_shops_id = set()
        self.map_geo = {}

        #for apple audit
        if request.user.id == 32:
            serializer.validated_data['latitude'] = 30.631876
            serializer.validated_data['longitude'] = 104.08892
            serializer.validated_data['city'] = '成都市'

        if (serializer.validated_data['search'] == 'around'):
            self.around(request, serializer, shop_type)
        elif (serializer.validated_data['search'] == 'name'):
            self.name(request, serializer, shop_type)
        elif (serializer.validated_data['search'] == 'collect'):
            self.collect(request, serializer, shop_type)
        elif (serializer.validated_data['search'] == 'nearby'):
            self.nearby(request, serializer)

        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = FindShopResponseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FindShopResponseSerializer(self.queryset, many=True)
        return Response(serializer.data)

    def around(self, request, serializer, shop_type=None):
        is_friend = False
        if 'friend' in serializer.data:
            is_friend = serializer.validated_data['friend']

        try:
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']
            city = serializer.validated_data['city']
        except:
            raise ValidationDict211Error("参数不对")

        list_geo = RedisIF.r.georadius('ShopGeo', longitude, latitude, 30000000, unit="m", withdist=True,
                                       sort='ASC')
        self.map_geo = {int(list_geo[i][0]): list_geo[i][1] for i in range(0, len(list_geo), 1)}

        for temp in list_geo:
            self.around_shops_id.add(temp[0])

        if len(self.around_shops_id) == 0:
            page = self.paginate_queryset([])

            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(serializer.data)

            return Response({})

        if is_friend:
            self.around_friend(request=request, shop_type=shop_type, city=city)
        else:
            self.around_mine(request=request, shop_type=shop_type, city=city)
            self.around_friend(request=request, shop_type=shop_type, city=city)
            self.around_other(request=request, shop_type=shop_type, city=city)

        self.queryset.sort(key=lambda query: (query.distance))

    def name(self, request, serializer, shop_type=None):
        try:
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']
            name = serializer.validated_data['name']
            city = serializer.validated_data['city']
        except:
            raise ValidationDict211Error("参数不对")

        filter = Q(name__contains=name) & Q(city=city) & Q(state=4)
        if shop_type:
            filter = filter & Q(type_id=shop_type)

        queryset = Shop.objects.filter(filter)

        for item in queryset:
            self.around_shops_id.add(str(item.id))
            self.map_geo[item.id] = None

        if len(self.around_shops_id) == 0:
            page = self.paginate_queryset([])

            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(serializer.data)

            return Response({})

        self.around_mine(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude, city=city)
        self.around_friend(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude, city=city)
        self.around_other(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude, city=city)

        self.queryset.sort(key=lambda query: (query.distance))

    def collect(self, request, serializer, shop_type=None):
        try:
            latitude = serializer.validated_data['latitude']
            longitude = serializer.validated_data['longitude']
        except:
            raise ValidationDict211Error("参数不对")

        sql = "SELECT S.id, C.id "\
            "FROM common_myuser AS U, common_collectshop AS C, common_shop AS S, common_shopfirsttype AS F "\
            "WHERE U.id = C.user_id AND C.shop_id = S.id AND S.type_id = F.id AND U.id = {0} ".format(request.user.id)

        if shop_type:
            sql = sql + ("AND type_id = {0}".format(shop_type))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        self.map_collect = {}

        for obj in fetchall:
            self.around_shops_id.add(str(obj[0]))
            self.map_geo[obj[0]] = None
            self.map_collect[obj[0]] = obj[1]

        if len(self.around_shops_id) == 0:
            page = self.paginate_queryset([])

            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(serializer.data)

            return Response({})

        self.around_mine(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude)
        self.around_friend(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude)
        self.around_other(request=request, shop_type=shop_type, latitude=latitude, longitude=longitude)

        for query in self.queryset:
            #order by collect time
            query.collect_id = self.map_collect[query.id]

        self.queryset.sort(key=lambda query: (query.collect_id), reverse=True)

    def nearby(self, request, serializer):
        try:
            shop_id = serializer.validated_data['shop']
        except:
            raise ValidationDict211Error("参数不对")

        shop_type = Shop.objects.get(pk=shop_id).type.id

        list_geo = RedisIF.r.georadiusbymember('ShopGeo', shop_id, 30000000, unit="m", withdist=True, sort='ASC', count=3)

        for i in range(0, len(list_geo), 1):
            if list_geo[i][0] == str(shop_id):
                list_geo.pop(i)
                break

        self.map_geo = {int(list_geo[i][0]): list_geo[i][1] for i in range(0, len(list_geo), 1)}

        for temp in list_geo:
            self.around_shops_id.add(temp[0])

        if len(self.around_shops_id) == 0:
            page = self.paginate_queryset([])

            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(serializer.data)

            return Response({})

        self.around_mine(request=request, shop_type=shop_type)
        self.around_friend(request=request, shop_type=shop_type)
        self.around_other(request=request, shop_type=shop_type)

        self.queryset.sort(key=lambda query: (query.distance))

    def fill(self, obj, request, latitude, longitude):
        serializer = self.serializer_class()
        serializer.id = obj[1]
        serializer.name = obj[2]
        serializer.distance = self.map_geo[obj[1]] \
            if self.map_geo[obj[1]] is not None else calcDistance(latitude, longitude, obj[3], obj[4])
        serializer.address = obj[5]
        serializer.ico = GetAbsoluteImageUrl(request, obj[6])
        serializer.level = obj[7]
        serializer.spokesman_id = obj[8]
        serializer.spokesman_ico = GetAbsoluteImageUrl(request, obj[9])

        serializer.activity_is_valid = obj[10]
        if serializer.activity_is_valid:
            serializer.activity_type = obj[11]
            if 1 == serializer.activity_type:
                serializer.activity_discount = obj[12]
                serializer.share = '商家活动{0}折'.format(obj[12] / 10)
            elif 2 == serializer.activity_type:
                serializer.activity_full_price = obj[13]
                serializer.activity_reduce_price = obj[14]
                serializer.share = '商家活动满{0}减{1}元'.format(obj[13], obj[14])

        return serializer

    def fill_mine(self, obj, request, latitude, longitude):
        serializer = self.fill(obj, request, latitude, longitude)

        temp = discount_describe_mine(obj[15], obj[16], obj[17], obj[18], obj[19])

        serializer.discount_is_valid = bool(temp)
        if serializer.discount_is_valid:
            serializer.discount_type = obj[16]
            serializer.discount = temp
            if 1 == serializer.discount_type:
                serializer.discount_discount = obj[17]
            elif 2 == serializer.discount_type:
                serializer.discount_full_price = obj[18]
                serializer.discount_reduce_price = obj[19]

        return serializer

    def fill_friend(self, obj, request, latitude, longitude):
        serializer = self.fill(obj, request, latitude, longitude)

        temp, temp2 = discount_describe_friend(obj[20], obj[15], obj[16], obj[17], obj[18], obj[19], obj[21])

        serializer.discount_is_valid = bool(temp)
        if serializer.discount_is_valid:
            serializer.discount_type = obj[16]
            serializer.discount = temp2
            if 1 == serializer.discount_type:
                serializer.discount_discount = temp
            elif 2 == serializer.discount_type:
                serializer.discount_full_price = obj[18]
                serializer.discount_reduce_price = temp

        return serializer

    def around_mine_normal(self, request, shop_type=None, city=None):
        str_shops_id = ",".join(self.around_shops_id)

        sql = "SELECT 'normal', S.id, S.name, S.latitude, S.longitude, S.address, S.ico, S.`level`, U.id, U.ico_thumbnail, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "LEFT JOIN common_myuser AS U ON U.id = S2.spokesman_id, "\
            "common_shopactivity AS A, common_shopdiscount AS D "\
            "WHERE S.state = 4 AND A.shop_id = S.id AND D.shop_id = S.id AND S2.type = 'normal' "\
            "AND U.id = {0} AND S.id in ({1})".format(request.user.id, str_shops_id)

        if shop_type:
            sql += " AND S.type_id = {0}".format(shop_type)
        if city:
            sql += " AND S.city = '{0}'".format(city)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def around_mine_member(self, request, shop_type=None, city=None):
        str_shops_id = ",".join(self.around_shops_id)

        sql = "SELECT 'member', S.id, S.name, S.latitude, S.longitude, S.address, S.ico, S.`level`, U.id, U.ico_thumbnail, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, " \
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id " \
            "LEFT JOIN common_shopmember AS M ON M.id = S2.member_id " \
            "LEFT JOIN common_myuser AS U ON U.id = M.user_id, "\
            "common_shopactivity AS A, common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "WHERE S.state = 4 AND M.shop_id = S.id AND M.user_id = U.id AND M2.id = M.member_card_id "\
            "AND A.shop_id = S.id AND S2.type = 'member' AND M.loose_change > 0 "\
            "AND U.id = {0} AND S.id in ({1})".format(request.user.id, str_shops_id)

        if shop_type:
            sql += " AND S.type_id = {0}".format(shop_type)
        if city:
            sql += " AND S.city = '{0}'".format(city)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def around_mine(self, request, shop_type=None, longitude=None, latitude=None, city=None):
        if len(self.around_shops_id) == 0:
            return

        f1 = self.around_mine_normal(request, shop_type, city)
        f2 = self.around_mine_member(request, shop_type, city)

        fetchall = []
        fetchall.extend(list(f1))
        fetchall.extend(list(f2))
        fetchall.sort(key=lambda k: k[1])

        for obj in fetchall:
            serializer = self.fill_mine(obj, request, latitude, longitude)

            self.around_shops_id.remove(str(obj[1]))

            combo = self.__combo(obj[1], serializer)
            if combo:
                serializer.combo = combo

            self.queryset.append(serializer)

    def around_friend_normal(self, request, shop_type=None, city=None):
        str_shops_id = ",".join(self.around_shops_id)

        sql = "SELECT 'normal', S.id, S.name, S.latitude, S.longitude, S.address, S.ico, S.`level`, U.id, U.ico_thumbnail, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price, "\
            "G.type, S3.discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "LEFT JOIN common_myuser AS U ON U.id = S2.spokesman_id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = U.id "\
            "LEFT JOIN common_friendgroup AS G ON F.group_id = G.id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON F.group_id = S3.group_id AND S.id = S3.shop_id, "\
            "common_shopactivity AS A, common_shopdiscount AS D "\
            "WHERE S.state = 4 AND S.id = A.shop_id AND S.id = D.shop_id AND S2.type = 'normal' "\
            "AND F.friend_id = {0} AND S.id IN ({1})".format(request.user.id, str_shops_id)

        if shop_type:
            sql += " AND type_id = {0}".format(shop_type)
        if city:
            sql += " AND S.city = '{0}'".format(city)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def around_friend_member(self, request, shop_type=None, city=None):
        str_shops_id = ",".join(self.around_shops_id)

        sql = "SELECT 'member', S.id, S.name, S.latitude, S.longitude, S.address, S.ico, S.`level`, U.id, U.ico_thumbnail, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price, " \
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price, " \
            "G.type, S3.member_discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopmember AS M ON M.id = S2.member_id "\
            "LEFT JOIN common_myuser AS U ON U.id = M.user_id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = U.id "\
            "LEFT JOIN common_friendgroup AS G ON F.group_id = G.id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON F.group_id = S3.group_id AND S.id = S3.shop_id, "\
            "common_shopactivity AS A, common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "WHERE S.state = 4 AND S.id = A.shop_id AND M.shop_id = S.id AND M.user_id = U.id "\
            "AND M2.id = M.member_card_id AND S2.type = 'member' AND M.loose_change > 0  " \
            "AND F.friend_id = {0} AND S.id IN ({1})".format(request.user.id, str_shops_id)

        if shop_type:
            sql += " AND type_id = {0}".format(shop_type)
        if city:
            sql += " AND S.city = '{0}'".format(city)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def around_friend(self, request, shop_type=None, longitude=None, latitude=None, city=None):
        if len(self.around_shops_id) == 0:
            return

        f1 = self.around_friend_normal(request, shop_type, city)
        f2 = self.around_friend_member(request, shop_type, city)

        fetchall = []
        fetchall.extend(list(f1))
        fetchall.extend(list(f2))
        fetchall.sort(key=lambda k: k[1])

        serializers = []
        count = 0
        id = None

        for obj in fetchall:
            serializer = self.fill_friend(obj, request, latitude, longitude)

            try:
                self.around_shops_id.remove(str(obj[1]))
            except:
                pass

            if (id is not None and count > 0 and obj[1] != id):
                rand = randint(0, len(serializers) - 1)

                combo = self.__combo(serializers[rand].id, serializers[rand])
                if combo:
                    serializers[rand].combo = combo

                self.queryset.append(serializers[rand])
                serializers.clear()
                count = 0

            id = obj[1]

            combo = self.__combo(serializer.id, serializer)
            if combo:
                serializer.combo = combo

            serializers.append(serializer)
            count += 1

        if count > 0:
            rand = randint(0, len(serializers) - 1)

            combo = self.__combo(serializers[rand].id, serializers[rand])
            if combo:
                serializers[rand].combo = combo

            self.queryset.append(serializers[rand])

    def around_other(self, request, shop_type=None, longitude=None, latitude=None, city=None):
        if len(self.around_shops_id) == 0:
            return

        str_shops_id = ",".join(self.around_shops_id)

        sql = "SELECT 'other', S.id, S.name, S.latitude, S.longitude, S.address, S.ico, S.`level`, U.id, U.ico_thumbnail, "\
            "A.is_valid, A.type, A.discount, A.full_price, A.reduce_price "\
            "FROM common_shop AS S "\
            "LEFT JOIN common_myuser AS U ON U.id = S.seller_id, " \
            "common_shopactivity AS A " \
            "WHERE S.state = 4 AND S.id = A.shop_id AND S.id IN ({0})".format(str_shops_id)

        if shop_type:
            sql = sql + (" AND type_id = {0}".format(shop_type))
        if city:
            sql = sql + (" AND S.city = '{0}'".format(city))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        for obj in fetchall:
            serializer = self.fill(obj, request, latitude, longitude)

            combo = self.__combo(obj[1], serializer)
            if combo:
                serializer.combo = combo

            self.queryset.append(serializer)

    def __combo(self, shop_id, serializer):
        combo = None
        queryset = ShopCombo.objects.filter(shop_id=shop_id, status='online')
        for item in queryset:
            if combo:
                combo += ' 等'
                break

            combo = (item.name + '  ' + str(item.activity_price) + '元')

        return combo

