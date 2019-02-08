from django.db import connection, transaction, IntegrityError
from django.db.models import Q
from SpokesTribe.settings import BROTHER_RATIO1, BROTHER_RATIO2
from math import radians, atan, tan, acos, sin, cos, ceil, floor
import random
from common.models import ShopSpoke, MyUser
from common.function import discount_describe_mine, discount_describe_friend, spoker_type


class ShopDiscountCalculate(object):
    def fill_spoker_dict(self, id, nick, ico, discount):
        self.spokesman['id'] = id
        self.spokesman['nick'] = nick
        self.spokesman['ico_thumbnail'] = ico
        self.spokesman['discount'] = discount

    def fill_discount_dict(self, valid, type=1, discount=100, full_price=100, reduce_price=0):
        self.discount['is_valid'] = valid
        self.discount['type'] = type
        self.discount['discount'] = discount
        self.discount['full_price'] = full_price
        self.discount['reduce_price'] = reduce_price

    def fill_discount_dict2(self, valid, type, discount, full_price=100):
        self.discount['is_valid'] = valid
        self.discount['type'] = type
        if 1 == type:
            self.discount['discount'] = discount
            # todo temp
            self.discount['full_price'] = 100
            self.discount['reduce_price'] = 0
        elif 2 == type:
            self.discount['full_price'] = full_price
            self.discount['reduce_price'] = discount
            # todo temp
            self.discount['discount'] = 100

    def calculate(self, request, shop_id, spokesman_id=None, spoke_type=None):
        shop_id = int(shop_id)
        self.spokesman = {}
        self.discount = {}

        if (not spokesman_id or request.user.id == spokesman_id) \
            and self.mine(shop_id=shop_id, user_id=request.user.id, type=spoke_type):
            pass
        elif self.friend(shop_id=shop_id, user_id=request.user.id, spoker_id=spokesman_id, type=spoke_type):
            pass
        else:
            self.other(shop_id=shop_id, spoker_id=spokesman_id)

        return self.spokesman, self.discount

    def mine_normal(self, shop_id, user_id):
        sql = "SELECT 'normal', U.id, U.nick_name, U.ico_thumbnail, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price "\
            "FROM common_shop AS S, common_shopdiscount AS D, common_shopspoke AS S2, common_myuser AS U "\
            "WHERE D.shop_id = S.id AND S2.shop_id = S.id AND S2.spokesman_id = U.id AND S2.type = 'normal' " \
            "AND U.id = {0} AND S.id = {1}".format(user_id, shop_id)

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def mine_member(self, shop_id, user_id):
        sql = "SELECT 'member', U.id, U.nick_name, U.ico_thumbnail, " \
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price "\
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

    def mine(self, shop_id, user_id, type=None):

        if not type:
            type = spoker_type(shop_id, user_id)

        if 'normal' == type:
            fetchall = self.mine_normal(shop_id, user_id)
        elif 'member' == type:
            fetchall = self.mine_member(shop_id, user_id)
        else:
            fetchall = self.mine_normal(shop_id, user_id)
            if 0 == len(fetchall):
                fetchall = self.mine_member(shop_id, user_id)

        for obj in fetchall:
            if 'member' == obj[0]:
                spoker_discount = discount_describe_mine(bool(obj[4]), obj[5], obj[6], obj[7], obj[8])
                self.fill_spoker_dict(obj[1], obj[2], obj[3], spoker_discount)
                self.fill_discount_dict(bool(obj[4]), obj[5], obj[6], obj[7], obj[8])
            else:
                spoker_discount = discount_describe_mine(obj[4], obj[5], obj[6], obj[7], obj[8])
                self.fill_spoker_dict(obj[1], obj[2], obj[3], spoker_discount)
                self.fill_discount_dict(obj[4], obj[5], obj[6], obj[7], obj[8])

            return True

        return False

    def friend_normal(self, shop_id, user_id, spoker_id=None):
        sql = "SELECT 'normal', U.id, U.nick_name, U.ico_thumbnail, "\
            "D.is_valid, D.type, D.discount, D.full_price, D.reduce_price, "\
            "G.type, S3.discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = S2.spokesman_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = F.group_id AND S3.shop_id = S.id, "\
            "common_friendgroup AS G, common_myuser AS U, common_shopdiscount AS D "\
            "WHERE S.id = {0} AND F.friend_id = {1} AND G.id = F.group_id AND F.user_id = U.id " \
            "AND S.id = D.shop_id AND S2.type = 'normal' "\
            .format(shop_id, user_id)

        if spoker_id:
            sql += ("AND U.id = {0} ".format(spoker_id))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def friend_member(self, shop_id, user_id, spoker_id=None):
        sql = "SELECT 'member', U.id, U.nick_name, U.ico_thumbnail, "\
            "CD.member_card_id, CD.type, CD.discount, CD.full_price, CD.reduce_price, " \
            "G.type, S3.member_discount "\
            "FROM common_shop AS S "\
            "RIGHT JOIN common_shopspoke AS S2 ON S2.shop_id = S.id "\
            "LEFT JOIN common_shopmember AS M ON M.id = S2.member_id "\
            "RIGHT JOIN common_friend AS F ON F.user_id = M.user_id "\
            "LEFT JOIN common_shopspokegroup AS S3 ON S3.group_id = F.group_id AND S3.shop_id = S.id, "\
            "common_friendgroup AS G, common_myuser AS U, "\
            "common_shopmembercard AS M2 "\
            "LEFT JOIN common_carddiscount AS CD ON CD.member_card_id = M2.id "\
            "WHERE S.id = {0} AND F.friend_id = {1} AND G.id = F.group_id AND F.user_id = U.id "\
            "AND M.shop_id = S.id AND M.user_id = U.id AND M2.id = M.member_card_id "\
            "AND S2.type = 'member' AND M.loose_change > 0 "\
            .format(shop_id, user_id)

        if spoker_id:
            sql += ("AND U.id = {0} ".format(spoker_id))

        cursor = connection.cursor()
        cursor.execute(sql)
        fetchall = cursor.fetchall()

        return fetchall

    def friend(self, shop_id, user_id, spoker_id=None, type=None):
        fetchall = []
        if 'normal' == type:
            fetchall = self.friend_normal(shop_id, user_id, spoker_id)
        elif 'member' == type:
            fetchall = self.friend_member(shop_id, user_id, spoker_id)
        else:
            f1 = self.friend_normal(shop_id, user_id)
            f2 = self.friend_member(shop_id, user_id)

            fetchall.extend(list(f1))
            fetchall.extend(list(f2))
            fetchall.sort(key=lambda k: k[1])

        for obj in fetchall:
            if 'member' == obj[0]:
                discount_discount, spoker_discount = discount_describe_friend(group_type=obj[9], is_valid=obj[4],
                    type=obj[5], discount=obj[6], full_price=obj[7], reduce_price=obj[8], friend_discount=obj[10])
                self.fill_spoker_dict(obj[1], obj[2], obj[3], spoker_discount)
                self.fill_discount_dict2(bool(discount_discount), obj[5], discount=discount_discount, full_price=obj[7])
            else:
                discount_discount, spoker_discount = discount_describe_friend(group_type=obj[9], is_valid=obj[4],
                    type=obj[5], discount=obj[6], full_price=obj[7], reduce_price=obj[8], friend_discount=obj[10])
                self.fill_spoker_dict(obj[1], obj[2], obj[3], spoker_discount)
                self.fill_discount_dict2(bool(discount_discount), obj[5], discount=discount_discount, full_price=obj[7])

            return True

        return False

    def other(self, shop_id, spoker_id=None):
        if spoker_id:
            user = MyUser.objects.get(pk=spoker_id)
            self.fill_spoker_dict(spoker_id, user.nick_name, user.ico_thumbnail, '')
        else:
            sql = "SELECT U.id, U.nick_name, U.ico_thumbnail " \
                  "FROM common_shop AS S " \
                  "LEFT JOIN common_myuser AS U ON U.id = S.seller_id " \
                  "WHERE S.id = {0}".format(shop_id)

            cursor = connection.cursor()
            cursor.execute(sql)
            fetchall = cursor.fetchall()

            for obj in fetchall:
                self.fill_spoker_dict(obj[0], obj[1], obj[2], '')
                break

        return True