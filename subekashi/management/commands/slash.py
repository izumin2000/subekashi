from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "テストコマンド"

    def handle(self, *args, **options):
        for song_ins in Song.objects.all() :
            if "/" in song_ins.title :
                print(song_ins.title, song_ins.id)
                song_ins.title = song_ins.title.replace("/", "╱")
                song_ins.save()