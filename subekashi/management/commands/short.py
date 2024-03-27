from django.core.management.base import BaseCommand
from subekashi.models import Song

class Command(BaseCommand) :
    def handle(self, *args, **options):
        beforeIds = [1352, 1353, 1430]
        afterIds = [7, 8, 9]
        songs = Song.objects.all()
        for beforeId, afterId in zip(beforeIds, afterIds) :
            songRec = songs.get(pk = beforeId)
            songRec.id = afterId
            songRec.issubeana = True
            songRec.save()
            self.stdout.write(self.style.SUCCESS(f"updated Song ID {songRec.id}"))
            
            for imitatedId in list(map(int, songRec.imitated.split(","))) :
                imitatedRec = songs.get(pk = imitatedId)
                imitatedRec.imitate = imitatedRec.imitate.replace(str(beforeId), str(afterId))
                imitatedRec.save()
                self.stdout.write(self.style.SUCCESS(f"updated Song ID {imitatedRec.id}"))
            
            songRec = songs.get(pk = beforeId)
            songRec.delete()