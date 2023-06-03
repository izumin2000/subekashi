from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "テストコマンド"

    def handle(self, *args, **options):
        for i in Song.objects.all() :
            if "/" in i.title :
                print(i.title, i.id)