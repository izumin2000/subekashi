from django.core.management.base import BaseCommand
from subekashi.models import Song
from django.utils import timezone


class Command(BaseCommand):
    help = "最終更新日のアップデート"

    def handle(self, *args, **options) :
        for songIns in Song.objects.filter(posttime = None) :
            songIns.posttime = timezone.now()
            songIns.save()