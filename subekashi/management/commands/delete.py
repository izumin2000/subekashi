from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "指定したSongを削除する"

    def add_arguments(self, parser):
        parser.add_argument('ids', nargs='+', type=int)
        parser.add_argument(
            '-k', '--keep-links',
            action='store_true',
            help='指定した場合、song.links.update(is_removed=True) を実行しない',
        )

    def handle(self, *args, **options):
        for song_id in options['ids']:
            try:
                song = Song.objects.get(pk=song_id)
                if not options['keep_links']:
                    song.links.update(is_removed=True)
                song.delete()
                self.stdout.write(self.style.SUCCESS(f"{song_id}を削除しました"))
            except Song.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"{song_id}は存在しません"))