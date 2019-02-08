from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter

from common.message_viewset import SystemMessageViewSet, NotifyMessageViewSet, TradeMessageViewSet
from .bill_viewset import TradeBuyerViewSet, TradeSpokesmanViewSet, TradeRefundViewSet, CashRecordViewSet
from .find_shops_viewset import FindShopViewSet
from .shop_viewset import ShopViewSet
from .shop_combo_viewset import ShopComboViewSet
from .party_view import PartyViewSet
from .views import SmsVerifyViewSet, ResumeViewSet, ShopSpokesViewSet, CollectShopViewSet, WalletViewSet, InterfaceViewSet, \
    ShopPhotoViewSet, FriendViewSet, BankcardViewSet, ShopCommentViewSet, Flyer2UserViewSet, FlyerDiscountViewSet, \
    FlyerReduceViewSet, FlyerExperienceViewSet
from .shop_member_viewset import ShopMemberCardViewSet, ShopMemberRechargeViewSet, ShopMemberViewSet, \
    ShopMemberRechargeAllViewSet, ShopMemberRechargeTimeViewSet, ShopMemberRechargeCountViewSet

# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'^sms', SmsVerifyViewSet)
router.register(r'^resume', ResumeViewSet)
router.register(r'^findshops', FindShopViewSet)
router.register(r'^shop', ShopViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/photos', ShopPhotoViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/combo', ShopComboViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/comment', ShopCommentViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_card', ShopMemberCardViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge', ShopMemberRechargeViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_time', ShopMemberRechargeTimeViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_count', ShopMemberRechargeCountViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_all', ShopMemberRechargeAllViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_discount', FlyerDiscountViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_reduce', FlyerReduceViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_experience', FlyerExperienceViewSet)
router.register(r'^shop_member', ShopMemberViewSet)
router.register(r'^spokes_shop', ShopSpokesViewSet)
router.register(r'^collect_shop', CollectShopViewSet)
router.register(r'^wallet', WalletViewSet)
router.register(r'^wallet/bankcard', BankcardViewSet)
router.register(r'^IF', InterfaceViewSet)
router.register(r'^friend', FriendViewSet)
router.register(r'^trade_buyer', TradeBuyerViewSet)
router.register(r'^trade_spokesman', TradeSpokesmanViewSet)
router.register(r'^trade_refund', TradeRefundViewSet)
router.register(r'^cash_record', CashRecordViewSet)
router.register(r'^message/system', SystemMessageViewSet)
router.register(r'^message/notify', NotifyMessageViewSet)
router.register(r'^message/trade', TradeMessageViewSet)
router.register(r'^party', PartyViewSet)
router.register(r'^flyer', Flyer2UserViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]