from django.core.management.base import BaseCommand
from subekashi.models import Song
from django.utils import timezone


class Command(BaseCommand):

    def handle(self, *args, **options):
        for songId in options['d'] :
            songIns = Song.objects.filter(pk = int(songId)).first()
            if songIns :
                print("delete song", songIns.id)
                songIns.delete()

        songInsL = Song.objects.all() 
        songInsSet = set()
        for songIns in songInsL :
            songInsSet.add(songIns.id)
            if songIns.imitated and songIns.imitated[0] == "," :
                songIns.imitated = songIns.imitated[1:]
                songIns.save()
                print("delete conma", songIns.id)

        deletedSongsSet = set(range(songInsL.last().id)) - songInsSet

        for songIns in songInsL :
            isChanged = False                

            # imitatedの削除
            imitated = songIns.imitated
            imitatedSet = set(map(int, imitated.split(","))) if bool(imitated) else set()
            if len(imitatedSet & deletedSongsSet) :
                imitatedL = list(imitatedSet - deletedSongsSet)
                imitated = ",".join(list(map(str, imitatedL))) if imitatedL else ""
                print("delete deleted imiteted song(s)", songIns.id)
                songIns.imitated = imitated
                isChanged = True

            # posttimeの埋め込み
            if songIns.posttime == None :
                songIns.posttime = timezone.now()
                print("fill time", songIns.id)
                isChanged = True
            
            # スラッシュの置換
            if "/" in songIns.title :
                songIns.title = songIns.title.replace("/", "╱")
                print("replace slash", songIns.id)
                isChanged = True
            
            if isChanged :
                songIns.save()

    def add_arguments(self, parser):
        parser.add_argument('-d', required=False, nargs='*')