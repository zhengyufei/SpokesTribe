from django.core.management.base import BaseCommand, CommandError
from myadmin.commands import shop_cash


#14:00
class Command(BaseCommand):
    args = ''
    help = 'shop cash to bankcard'

    def handle(self, *args, **options):
        shop_cash()
