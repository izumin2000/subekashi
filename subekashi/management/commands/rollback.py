from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "ロールバック"

    def handle(self, *args, **options) :
        