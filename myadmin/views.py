# Create your views here.
import json

from rest_framework import viewsets, permissions
from rest_framework.decorators import list_route
from rest_framework.response import Response

from APNS import apns_seller
from APNS.yunbaSDK import YunbaBuyer
from IM.IM import IM as im
from Pay.Zhaoshang.ZhaoshangTransfer import PayForAnother
from common.models import MyUser, FriendGroup, Shop, Wallet, ShopSpoke, ShopSpokeGroup, \
    ShopWallet, CashRecord
from common.serializers import EmptySerializer


class TestViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def test_add(self, request, *args, **kwargs):
        from MyAbstract.funtions import GetFixedImageUrl
        user = MyUser.objects.get(pk=6)
        return Response(im.add('32132132100', '钢铁侠sick', GetFixedImageUrl(request, user.ico_thumbnail)))

    @list_route(methods=['get'])
    def user_spokes_shop(self, request, *args, **kwargs):
        user = MyUser.objects.get(username='13512340001')
        group = FriendGroup.objects.get(user=user, type=3)

        query = Shop.objects.all()
        for shop in query:
            if not ShopSpoke.objects.filter(spokesman=user, shop=shop).exists():
                ShopSpoke.objects.create(shop=shop, spokesman=user, type='normal')
            if not ShopSpokeGroup.objects.filter(shop=shop, group=group).exists():
                ShopSpokeGroup.objects.create(shop=shop, group=group, discount=90)
            shop.spoke_count += 1
            shop.save(update_fields=['spoke_count'])

        return Response('')

    @list_route(methods=['get'])
    def patch_wallet(self, request, *args, **kwargs):
        queryset = Wallet.objects.all()

        for query in queryset:
            if len(query.password) < 24:
                query.set_unusable_password()
                query.save(update_fields=['password'])

        return Response('')

    @list_route(methods=['get'])
    def patch_shop_wallet(self, request, *args, **kwargs):
        queryset = ShopWallet.objects.all()

        for query in queryset:
            if len(query.password) < 24:
                query.set_unusable_password()
                query.save(update_fields=['password'])

        return Response('')

    @list_route(methods=['get'])
    def pulish_alias(self, request, *args, **kwargs):
        yunba = YunbaBuyer()
        return yunba.send_publish2_to_alias('13438891197', 'this is title', 'this is test', 'agent', '1487179663')

    @list_route(methods=['get'])
    def pulish_alias2(self, request, *args, **kwargs):
        yunba = YunbaBuyer()
        return yunba.send_publish2_to_alias('15982002374', 'this is title', 'this is test', 'agent', '1487179663')

    #@list_route(methods=['get'])
    #def pulish_alias3(self, request, *args, **kwargs):
    #    return apns.pulish_alias_system('13408544339', 'this is system message')

    #@list_route(methods=['get'])
    #def pulish_alias4(self, request, *args, **kwargs):
    #    return apns.pulish_alias_notify('13438891197', 1, "您申请成为'山寨火锅'代理已成功。")#13438891197

    #@list_route(methods=['get'])
    #def pulish_alias5(self, request, *args, **kwargs):
    #    return apns.publish_alias_trade('13438891197', "新的交易。")

    #@list_route(methods=['get'])
    #def pulish_alias6(self, request, *args, **kwargs):
    #    return apns.pulish_alias_notify('13438891197', 100, "测试消息")  #13438891197

    @list_route(methods=['get'])
    def pulish_alias7(self, request, *args, **kwargs):
        shop = Shop.objects.get(pk=1)
        apns_seller.publish_alias_notify(shop, 100, "测试消息")  # 13438891197

        return Response({})

    @list_route(methods=['get'])
    def add_friend(self, request, *args, **kwargs):
        user = MyUser.objects.get(username='13408544339')
        rtn = im.add_friend('13408544339', '13096318115')

        return Response(rtn)

    @list_route(methods=['get'])
    def del_friend(self, request, *args, **kwargs):
        return Response(im.del_friend('13408544339', '13096318115'))

    @list_route(methods=['get'])
    def test_cash(self, request, *args, **kwargs):
        cash = CashRecord()
        number = cash.create_number()
        return Response(number)

    @list_route(methods=['get'])
    def test_pay_for_another(self, request, *args, **kwargs):
        import uuid
        #tmp = PayForAnother(str(int(uuid.uuid1().hex, 16))[0:10], '民生银行', '6226192005028147', '郑宇飞', 1.5)
        #tmp = PayForAnother(str(int(uuid.uuid1().hex, 16))[0:10], '招商银行', '6214830155471633', '张宇航', 1.5)
        tmp = PayForAnother(str(int(uuid.uuid1().hex, 16))[0:10], '招商银行', '6225880230596877', '开翔114', 1.5)
        #tmp = PayForAnother('1234567891', '招商银行', '755916031110802', '成都脸王科技有限公司', 1.5)
        response = str(tmp.post(), encoding="utf-8")
        return Response({'response':json.loads(response)})

    @list_route(methods=['get'])
    def test_payback(self, request, *args, **kwargs):
        from Pay.Zhaoshang.ZhaoshangTransfer import PayCallback
        callback = PayCallback('')
        callback.CheckSign()
        callback.ParseBUSDAT()
        print(callback.ParseBUSDAT())

        return Response('')

    @list_route(methods=['get'])
    def test_ali_refund(self, request, *args, **kwargs):
        from Pay.Ali.alipay import BuyerPay
        tmp = BuyerPay().refund('20170320092150441160772606836631', '0.01', '1234567890')
        print(tmp)

        return Response(tmp)

    @list_route(methods=['get'])
    def test_weixin_refund(self, request, *args, **kwargs):
        from Pay.Weixin import weixinpay
        pub = weixinpay.RefundPub(type='APP')
        cmd = {"out_trade_no": '20170324142823275954768894196561',
               "out_refund_no": '1234567890',
               "total_fee": 1,# 单位分
               "refund_fee": 1,
               "op_user_id": "1234567"
               }
        pub.updateParameter(**cmd)

        tmp = pub.getResult()
        print(tmp)

        return Response(tmp)
    
    def test_refund1(self, request, *args, **kwargs):
        from common.refund import Refund
        Refund().auto('20171010175944252168452132455127')
        return Response('')

    @list_route(methods=['get'])
    def test_refund2(self, request, *args, **kwargs):
        from common.refund import Refund
        Refund().auto_ticket('20170325150627192171944858539148', ['192193753994', '192195281513', '192179999985'])
        return Response('')

    @list_route(methods=['get'])
    def test_corp(self, request, *args, **kwargs):
        import urllib
        from MyAbstract.funtions import post
        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=wx062e89175e0a76a2&corpsecret=6AMPm7zV3LJOcpjDonZxH9vqkmFgtbxTJ9q7tnIBdDE8yTrFEX-71y01DHP7Y_TE'
        access_token = json.loads(urllib.request.urlopen(url=url).read().decode('utf-8'))['access_token']

        url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % access_token
        postdata = '{ \
            "touser": "zyf", \
            "toparty": "@all", \
            "totag": "@all", \
            "msgtype": "text", \
            "agentid": 0, \
            "text": { \
               "content": "Holiday Request For Pony(http://xxxxx)" \
            }, \
            "safe":0 \
            }'

        return Response(post(url, postdata))

    @list_route(methods=['get'])
    def test(self, request, *args, **kwargs):
        temp = request.user.marketserveremployeeship_set

        print('test', temp)
        print('test', temp.count())
        print('test', temp is None)

        return Response('')

from common.models import ShopWithdrawRecord

class Test2ViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.AllowAny]
    serializer_class = EmptySerializer

    @list_route(methods=['post'])
    def test(self, request, *args, **kwargs):
        queryset = ShopWithdrawRecord.objects.filter(status='retry')

        for item in queryset:
            response = PayForAnother(item.number, item.request_bank_name, item.request_acc_no,
                                     item.request_acc_name, item.cash)
            response = json.loads(str(response.post(), encoding="utf-8"))
            print('test', response)

        queryset.update(status='apply')

        return Response({'detail': request.data})