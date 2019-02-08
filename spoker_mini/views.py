import datetime
from django.db import connection
from django.db.models import F, Q
from rest_framework import parsers, renderers, viewsets, permissions, generics, mixins, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from MyAbstract.funtions import calcDistance
from common.models import MyUser, ShopMember, ShopFlyer, Flyer2User
from common.serializers import EmptySerializer, LatitudeReqireFilterSerializer
from .serializers import CardPackageHomeSerializer, MemberCardIntroSerializer, ShopMemberSerializer, \
    FlyerIntroSerializer, ShopFlyerSerializer


class CardPackageViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def home(self, request, *args, **kwargs):
        serializer = LatitudeReqireFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']

        members = ShopMember.objects.filter(user=request.user).order_by('-id')
        flyers = Flyer2User.objects.filter(user=request.user, status='valid').order_by('-id')

        flyers2 = []

        for item in flyers[:2]:
            item.flyer.distance = int(calcDistance(item.flyer.shop.latitude, item.flyer.shop.longitude, latitude, longitude))
            flyers2.append(item.flyer)

        temp = CardPackageHomeSerializer()
        temp.card_amount = members.count()
        temp.member_cards = members[:3]
        temp.flyer_amount = flyers.count()
        temp.flyers = flyers2

        serializer = CardPackageHomeSerializer(temp)

        return Response(serializer.data)

class ShopMemberViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = ShopMember.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopMemberSerializer

    def list(self, request, *args, **kwargs):
        queryset = ShopMember.objects.filter(user=request.user)

        serializer = MemberCardIntroSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = ShopMember.objects.get(user=request.user, shop_id=kwargs['pk'])

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

class Flyer2UserViewSet(mixins.RetrieveModelMixin,
                    mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Flyer2User.objects.all()
    permission_classes = [permissions.IsAuthenticated, ]
    serializer_class = ShopFlyerSerializer

    def list(self, request, *args, **kwargs):
        serializer = LatitudeReqireFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']

        queryset = Flyer2User.objects.filter(user=request.user, status='valid')

        flyers = []

        for item in queryset:
            if 3 == item.flyer.type:
                item.flyer.ticket_number = item.ticket_number
            item.flyer.distance = int(calcDistance(item.flyer.shop.latitude, item.flyer.shop.longitude, latitude, longitude))
            flyers.append(item.flyer)

        page = self.paginate_queryset(flyers)

        if page is not None:
            serializer = FlyerIntroSerializer(flyers, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = FlyerIntroSerializer(flyers, many=True, context=self.get_serializer_context())
        return Response({'results': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = LatitudeReqireFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']

        flyer = ShopFlyer.objects.get(pk=kwargs['pk'])
        flyer.distance = int(calcDistance(flyer.shop.latitude, flyer.shop.longitude, latitude, longitude))

        serializer = self.serializer_class(flyer, context=self.get_serializer_context())

        return Response(serializer.data)
