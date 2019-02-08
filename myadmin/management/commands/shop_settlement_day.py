from django.core.management.base import BaseCommand, CommandError
from myadmin.commands import ShopSettlement

#00:00
class Command(BaseCommand):
    args = ''
    help = 'shop settlement'

    def handle(self, *args, **options):
        ShopSettlement.shop_settlement(name='settle')
