import decimal
import json
from urllib.parse import quote
from django.db.models import Q
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from django.utils import timezone

from MyAbstract.exceptions import ValidationDict211Error
from common.models import Party, PartyPerson, PartyMessageBoard
from .serializers import PartySerializer, PartyListSerializer, PartyJoinSerializer, PartyPersonSerializer, \
    PartyCreateSerializer, PartyMessageBoardSerializer

class PartyViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    queryset = Party.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PartySerializer

    def list(self, request, *args, **kwargs):
        if 'type' in request.query_params:
            type = request.query_params['type']

            filter = Q(persons__user=request.user)

            if 'current' == type:
                filter &= Q(end_time__gt=timezone.now())
                filter &= ~Q(status='cancel')
            elif 'history' == type:
                filter &= Q(end_time__lte=timezone.now())
                filter &= ~Q(status='cancel')
        else:
            filter = Q(end_time__gt=timezone.now()) & ~Q(status='cancel')

        queryset = Party.objects.filter(filter).order_by('begin_time')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PartyListSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = PartyListSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = PartyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        party = serializer.save(organizer=request.user)
        PartyPerson.objects.create(party=party, user=request.user, person_count=1)

        return Response({'detail': 'OK'}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.end_time < timezone.now():
            instance.status = 'over'
            instance.save(update_fields=['status',])
        instance.has_joined = PartyPerson.objects.filter(party_id=instance.id, user=request.user).exists()
        instance.is_organizer = (request.user == instance.organizer)

        serializer = self.serializer_class(instance, context=self.get_serializer_context())

        return Response(serializer.data)

    @detail_route(methods=['post'])
    def join(self, request, pk=None):
        instance = self.get_object()
        if instance.end_time < timezone.now():
            raise ValidationDict211Error('活动已结束')

        count = 0
        for person in instance.persons.all():
            count += person.person_count

        serializer = PartyJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count += serializer.validated_data['person_count']

        party = Party.objects.get(pk=pk)

        if party.max_persons and count > party.max_persons:
            raise ValidationDict211Error('活动人数上限%d人' % party.max_persons)

        try:
            serializer.save(party=party, user=request.user)
        except:
            raise ValidationDict211Error('已经报名活动')

        return Response({'result': 'OK'})

    @detail_route(methods=['post'])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        if instance.end_time < timezone.now():
            raise ValidationDict211Error('活动已结束')

        if instance.organizer == request.user:
            instance.status = 'cancel'
            instance.save(update_fields=['status'])
        else:
            PartyPerson.objects.filter(party_id=pk, user=request.user).delete()

        return Response({'result': 'OK'})

    @detail_route(methods=['get'])
    def persons(self, request, pk=None):
        instance = self.get_object()
        serializer = PartyPersonSerializer(instance.persons.all().order_by('-id'), many=True, context=self.get_serializer_context())

        return Response({'results': serializer.data})

    @detail_route(methods=['get'])
    def share_url(self, request, pk=None):
        temp = 'http://www.dailibuluo.com/WeixinDevelop/activity?action=enter&activity_id=%d' \
               % (int(pk))

        url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx3e305e5a9bdc6ba6' \
              '&redirect_uri=%s&response_type=code&scope=snsapi_userinfo&state=STATE#wechat_redirect' % quote(temp)

        return Response({'url': url})

    @detail_route(methods=['get', 'post'])
    def message_board(self, request, pk=None):
        if request.method == 'GET':
            queryset = PartyMessageBoard.objects.filter(party__id=pk).order_by('-id')
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = PartyMessageBoardSerializer(page, many=True, context=self.get_serializer_context())
                return self.get_paginated_response(serializer.data)

            serializer = PartyMessageBoardSerializer(queryset, many=True, context=self.get_serializer_context())
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = PartyMessageBoardSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            instance = self.get_object()
            if instance.end_time < timezone.now():
                raise ValidationDict211Error('活动已结束')

            if instance.persons.all().filter(user__in=(request.user,)).exists():
                serializer.save(party=instance, user=request.user)
            else:
                raise ValidationDict211Error('未参加此活动')

            return Response({'result': 'OK'})