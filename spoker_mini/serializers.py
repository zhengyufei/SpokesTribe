from rest_framework import serializers
from MyAbstract.fields import CompressBase64ImageField
from MyAbstract.serializers import MyModelSerializer
from common.models import ShopMember, ShopFlyer


class MemberCardIntroSerializer(MyModelSerializer):
    shop_id = serializers.IntegerField(source='shop.id')
    shop_ico = serializers.ImageField(source='shop.ico_thumbnail')
    shop_name = serializers.CharField(source='shop.name')
    card_name = serializers.CharField(source='member_card.name')
    card_image = serializers.ImageField(source='member_card.image')

    class Meta:
        model = ShopMember
        fields = ('shop_id', 'shop_ico', 'shop_name', 'card_name', 'card_image')
        read_only_fields = ('shop_id', 'shop_ico', 'shop_name', 'card_name', 'card_image')

class FlyerIntroSerializer(MyModelSerializer):
    shop_name = serializers.SerializerMethodField()
    combo_name = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    full_price = serializers.SerializerMethodField()
    reduce_price = serializers.SerializerMethodField()

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'valid_period_end', 'shop_name', 'combo_name',
                  'distance', 'discount', 'full_price', 'reduce_price')
        custom_fields = ('shop_name', 'combo_name', 'distance', 'discount', 'full_price', 'reduce_price')

    def get_shop_name(self, obj):
        return obj.shop.name if 3 != obj.type else None

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

    def get_distance(self, obj):
        return obj.distance

    def get_discount(self, obj):
        return obj.discount.discount if 1 == obj.type else None

    def get_full_price(self, obj):
        return obj.reduce.full_price if 2 == obj.type else None

    def get_reduce_price(self, obj):
        return obj.reduce.reduce_price if 2 == obj.type else None

class CardPackageHomeSerializer(serializers.Serializer):
    card_amount = serializers.IntegerField()
    member_cards = MemberCardIntroSerializer(many=True)
    flyer_amount = serializers.IntegerField()
    flyers = FlyerIntroSerializer(many=True)

class ShopMemberSerializer(MyModelSerializer):
    shop_ico = serializers.ImageField(source='shop.ico_thumbnail')
    shop_name = serializers.CharField(source='shop.name')
    card_name = serializers.CharField(source='member_card.name')
    card_image = serializers.ImageField(source='member_card.image')
    number = serializers.CharField(source='id')
    discount = serializers.SerializerMethodField()

    def get_discount(self, obj):
        if hasattr(obj.member_card, 'discount'):
            return obj.member_card.discount.discount
        else:
            return 100

    class Meta:
        model = ShopMember
        fields = ('shop_ico', 'shop_name', 'card_name', 'card_image', 'loose_change', 'discount',  'number')
        custom_fields = ('discount')

class ShopFlyerSerializer(MyModelSerializer):
    shop_id = serializers.IntegerField(source='shop.id')
    shop_ico = serializers.ImageField(source='shop.ico_thumbnail')
    shop_name = serializers.CharField(source='shop.name')
    address = serializers.CharField(source='shop.address')
    latitude = serializers.DecimalField(source='shop.latitude', max_digits=14, decimal_places=12)
    longitude = serializers.DecimalField(source='shop.longitude', max_digits=15, decimal_places=12)
    phone = serializers.CharField(source='shop.phone')
    combo_name = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    lowest = serializers.SerializerMethodField()
    full_price = serializers.SerializerMethodField()
    reduce_price = serializers.SerializerMethodField()

    class Meta:
        model = ShopFlyer
        fields = ('id', 'type', 'img', 'shop_id', 'shop_ico', 'shop_name', 'address', 'latitude',
                  'longitude', 'phone', 'combo_name', 'distance', 'discount', 'full_price', 'reduce_price',
                  'valid_period_end', 'precautions', 'tips', 'lowest')
        custom_fields = ('combo_name', 'discount', 'full_price', 'reduce_price', 'lowest')

    def get_combo_name(self, obj):
        return obj.experience.name if 3 == obj.type else None

    def get_distance(self, obj):
        return obj.distance

    def get_discount(self, obj):
        return obj.discount.discount if 1 == obj.type else None

    def get_lowest(self, obj):
        return obj.discount.full_price if 1 == obj.type else None

    def get_full_price(self, obj):
        return obj.reduce.full_price if 2 == obj.type else None

    def get_reduce_price(self, obj):
        return obj.reduce.reduce_price if 2 == obj.type else None
