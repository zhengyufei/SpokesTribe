from django.db import connection
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import parsers, renderers, viewsets, permissions, generics, mixins, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from MyAbstract.exceptions import ValidationDict211Error
from MyAbstract.funtions import GetAbsoluteImageUrl

from common.models import MyUser, Friend
from common.serializers import EmptySerializer
from IM.IM import IM as im

class IMViewSet(viewsets.GenericViewSet):
    queryset = MyUser.objects.none()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = EmptySerializer

    @list_route(methods=['get'])
    def im_update(self, request, *args, **kwargs):
        self.del_all_friends()

        #im.batch_add()
        #self.modify_all_info(request)

        return Response('')

    def del_all_friends(self):
        queryset = MyUser.objects.all()

        for item in queryset:
            im.del_all_friends(item.id)

    def modify_all_info(self, request):
        queryset = MyUser.objects.all()

        for item in queryset:
            major_type = item.spoke_profile.major_shop.type.name if item.spoke_profile.major_shop else ''
            #im.modify_info(str(item.id), item.nick_name, item.ico, major_type)
            im.modify_nick(str(item.id), item.nick_name)
            im.modify_ico(str(item.id), GetAbsoluteImageUrl(request, item.ico))
            im.modify_major_spokes(str(item.id), major_type)

    @list_route(methods=['get'])
    def import_all_friend(self, request, *args, **kwargs):
        queryset = Friend.objects.all()

        dict_group = {}
        for item in queryset:
            if not item.user.id in dict_group:
                dict_group[item.user.id] = {}
            if not item.group.name in dict_group[item.user.id]:
                dict_group[item.user.id][item.group.name] = []
            dict_group[item.user.id][item.group.name].append((item.friend.id, item.alias if item.alias else ''))

        for (key, value) in dict_group.items():
            im.import_friend(key, value)

        return Response('')

    @list_route(methods=['get'])
    def modify_all_friend_allow_type(self, request, *args, **kwargs):
        queryset = MyUser.objects.all()

        for item in queryset:
            im.modify_allow_type(str(item.id))

        return Response('')