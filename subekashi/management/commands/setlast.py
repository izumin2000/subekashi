from django.core.management.base import BaseCommand
from subekashi.models import Singleton
from datetime import date


class Command(BaseCommand):
    help = "最終更新日のアップデート"

    def handle(self, *args, **options) :
            singletonIns, _ = Singleton.objects.update_or_create(key = "lastModified", defaults = {"key": "lastModified"})
            singletonIns.key = "lastModified"
            v = options['v']
            today = date.today().strftime("%Y-%m-%d")
            singletonIns.value = f"{today} (ver.{v})" if v else today
            singletonIns.save()
            
    def add_arguments(self, parser):
        parser.add_argument('--v', required=False, type=str)