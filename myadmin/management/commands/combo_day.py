from django.core.management.base import BaseCommand, CommandError
from myadmin.commands import combo_check

#00:00
class Command(BaseCommand):
    args = ''
    help = 'combo outtime'

    def handle(self, *args, **options):
        combo_check()
