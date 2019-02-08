from django.conf.urls import url, include
from rest_framework.routers import SimpleRouter, DefaultRouter

from common.message_viewset import SystemMessageViewSet, NotifyMessageViewSet, TradeMessageViewSet
from .views import ShopRequestViewSet,ShopSpokerViewSet, SmsVerifyViewSet, \
    InterfaceViewSet, WalletViewSet, TradeDiscountViewSet, ShopComboViewSet,\
    TradeTicketViewSet, TradeShopViewSet, CashRecordViewSet, \
    FlyerViewSet, FlyerDiscountViewSet, FlyerReduceViewSet, FlyerExperienceViewSet, Flyer2ShopMineViewSet, \
    Flyer2ShopOtherViewSet, FlyerTradeMineViewSet, FlyerTradeOtherViewSet, ShopPhotoViewSet, \
    TradeViewSet, TradeMemberViewSet, TradeExperienceViewSet, TradeRefundViewSet, TradeBonusViewSet, ShopManagerViewSet
from .shop_viewset import ShopViewSet
from .shop_member_viewset import ShopMemberCardViewSet, ShopMemberRechargeViewSet, ShopMemberServiceViewSet, \
    ShopMemberRechargeTimeViewSet, ShopMemberRechargeCountViewSet, ShopMemberViewSet, ShopMemberRechargeAllViewSet


# Create a router and register our viewsets with it.
router = SimpleRouter()

router.register(r'^sms', SmsVerifyViewSet)
router.register(r'^IF', InterfaceViewSet)
router.register(r'^shop', ShopViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/photo', ShopPhotoViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/manager', ShopManagerViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/combo', ShopComboViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/request', ShopRequestViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/spoker', ShopSpokerViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/wallet', WalletViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_all', TradeViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_discount', TradeDiscountViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_ticket', TradeTicketViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_member', TradeMemberViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_experience', TradeExperienceViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_refund', TradeRefundViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_shop', TradeShopViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/trade_bonus', TradeBonusViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_card', ShopMemberCardViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge', ShopMemberRechargeViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_service', ShopMemberServiceViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_time', ShopMemberRechargeTimeViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_count', ShopMemberRechargeCountViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member_recharge_all', ShopMemberRechargeAllViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/member', ShopMemberViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/cash_record', CashRecordViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer', FlyerViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_discount', FlyerDiscountViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_reduce', FlyerReduceViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_experience', FlyerExperienceViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_mine', Flyer2ShopMineViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_other', Flyer2ShopOtherViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_trade_mine', FlyerTradeMineViewSet)
router.register(r'^shop/(?P<pk_shop>[0-9]+)/flyer_trade_other', FlyerTradeOtherViewSet)
router.register(r'^message/system', SystemMessageViewSet)
router.register(r'^message/notify', NotifyMessageViewSet)
router.register(r'^message/trade', TradeMessageViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]