from rest_framework import viewsets, permissions, generics, mixins, views, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from MyAbstract.funtions import timetuple

from .models import SystemMessage, NotifyMessage, TradeMessage, Trade
from .serializers import SystemMessageSerializer, NotifyMessageSerializer, TradeMessageSerializer
from SpokesTribe.settings import TIME_ZONE
import time, pytz

class SystemMessageViewSet(viewsets.GenericViewSet):
    queryset = SystemMessage.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = SystemMessageSerializer

    def list(self, request, *args, **kwargs):
        queryset = SystemMessage.objects.all().order_by('-id')[0:20]

        for query in queryset:
            query.time = timetuple(query.time)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())

        return Response({'results': serializer.data})

class NotifyMessageViewSet(mixins.ListModelMixin,
                           viewsets.GenericViewSet):
    queryset = NotifyMessage.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = NotifyMessageSerializer

    def list(self, request, *args, **kwargs):
        queryset = NotifyMessage.objects.filter(user=request.user).order_by('-id')[0:20]

        for query in queryset:
            query.time = timetuple(query.time)

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())

        return Response({'results': serializer.data})

class TradeMessageViewSet(viewsets.GenericViewSet):
    queryset = TradeMessage.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = TradeMessageSerializer

    def list(self, request, *args, **kwargs):
        queryset = TradeMessage.objects.filter(user=request.user, status__in=(1, 2)).order_by('-id')[0:20]

        for query in queryset:
            query.time = timetuple(query.time)
            query.ban_jump = False

            #set ban when brokerage is zero
            if query.status == 1 and query.event == 1:#buyer discount buy
                query.image = query.record.trade.shop.ico_thumbnail
                query.type = 'expend'
                query.trade_type = query.record.trade.profile_type
            elif query.status == 2 and query.event == 1:#agent discount buy
                query.image = query.record.trade.buyer.ico_thumbnail
                query.type = 'income'
                query.trade_type = query.record.trade.profile_type
                if 0 == query.record.trade.tradediscountprofile.brokerage:
                    query.ban_jump = True
            elif query.status == 2 and query.event == 2:#agent discount confirm
                query.image = query.record.trade.shop.ico_thumbnail
                query.type = 'income'
                query.trade_type = query.record.trade.profile_type
                query.ban_jump = True if 0 == query.record.trade.tradediscountprofile.brokerage else False
            elif query.status == 1 and query.event == 4:#buyer tickets use
                query.image = query.record.ticket.trade.shop.ico_thumbnail
                query.type = 'expend'
                query.trade_type = query.record.ticket.trade.profile_type
            elif query.status == 2 and query.event == 4:#agent tickes use
                query.image = query.record.ticket.trade.buyer.ico_thumbnail
                query.type = 'income'
                query.trade_type = query.record.ticket.trade.profile_type
                query.ban_jump = True if 0 == query.record.ticket.brokerage else False
            elif query.status == 1 and query.event == 6:#buyer member charge
                query.image = query.record.trade.shop.ico_thumbnail
                query.type = 'expend'
                query.trade_type = query.record.trade.profile_type

            if query.record.trade:
                query.trade_number = query.record.trade.trade_number
                if query.record.trade.profile_type == 'discount':
                    if query.record.trade.tradediscountprofile.status == 'confirm':
                        query.status = '已结佣'
                    else:
                        query.status = '其他'
                elif query.record.trade.profile_type == 'member':
                    query.status = '充值'
            else:
                query.ticket_number = query.record.ticket.ticket_number
                if query.record.ticket.status == 'confirm':
                    query.status = '已使用'
                else:
                    query.status = '其他'

        serializer = self.serializer_class(queryset, many=True, context=self.get_serializer_context())

        return Response({'results': serializer.data})