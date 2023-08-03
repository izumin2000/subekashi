from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):

    def handle(self, *args, **options):
        songs = Song.objects.all() 
        songsSet = set()
        for song in songs :
            songsSet.add(song.id)
            if song.imitated and song.imitated[0] == "," :
                song.imitated = song.imitated[1:]
                song.save()
                print("delete conma", song.id, song.imitated)

        deletedSongsSet = set(range(songs.last().id)) - songsSet

        for song in songs :
            imitated = song.imitated
            imitatedSet = set(map(int, imitated.split(","))) if bool(imitated) else set()
            if len(imitatedSet & deletedSongsSet) :
                imitatedL = list(imitatedSet - deletedSongsSet)
                imitated = ",".join(list(map(str, imitatedL))) if imitatedL else ""
                print("delete deleted imiteted song(s)", song.id, imitated)
                song.imitated = imitated
                song.save()