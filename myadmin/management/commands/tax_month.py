from django.core.management.base import BaseCommand, CommandError
from myadmin.commands import tax

#15 00:00
class Command(BaseCommand):
    args = ''
    help = 'tax every month'

    def handle(self, *args, **options):
        tax()
