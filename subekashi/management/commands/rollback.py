from django.core.management.base import BaseCommand
from subekashi.models import Song
import pickle
from itertools import zip_longest
from django.utils import timezone

class Command(BaseCommand):
    help = "ロールバック"

    def handle(self, *args, **options) :
        fileName = options['f']
        SongL = list(Song.objects.all())
        with open(f'backups/{fileName}.pkl', 'rb') as f:
            backupSongL = pickle.load(f)

        for song, backupSong in zip_longest(SongL, backupSongL) :
            if song:
                songIns = Song.objects.get(pk = song.id)
            if not backupSong and not options['save'] :
                songIns.delete()
                continue
            if backupSong :
                songIns = Song(**backupSong)
                songIns.posttime = timezone.now()
                songIns.save()

    def add_arguments(self, parser):
        parser.add_argument('-f', required=True, type=str)
        parser.add_argument('-save', required=False, action='store_true')