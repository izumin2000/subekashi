from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "指定したSongを削除する"

    def add_arguments(self, parser):
        parser.add_argument('-d', required=True, nargs='+', type=int)

    def handle(self, *args, **options):
        for song_id in options['d']:
            try:
                song = Song.objects.get(pk=song_id)
                for link in song.links.all():
                    link.is_removed = True
                    link.save()
                song.delete()
                self.stdout.write(self.style.SUCCESS(f"{song_id}を削除しました"))
            except Song.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"{song_id}は存在しません"))
