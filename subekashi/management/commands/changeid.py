from django.core.management.base import BaseCommand
from subekashi.models import Song

class Command(BaseCommand):
    def change_relation(self, song, id, to, is_imitate=True):
        r  = song.imitate if is_imitate else song.imitated
        
        if not r:
            return
        
        for i in r.split(","):
            song = Song.objects.get(pk = i)
            l = song.imitate.split(",") if not is_imitate else song.imitated.split(",")
            l.remove(str(id))
            l.append(str(to))
            l_str = ",".join(l)
            if is_imitate:
                song.imitated = l_str
            else:
                song.imitate = l_str
            song.save()
    
    def handle(self, *args, **options):
        id = options['id']
        to = options['to']
        
        song = Song.objects.get(pk = id)
        
        song.id = to
        self.change_relation(song, id, to)
        self.change_relation(song, id, to, False)
        song.save()
        
        song = Song.objects.get(pk = id)
        song.delete()
        
    def add_arguments(self, parser):
        parser.add_argument('id', type=int)
        parser.add_argument('to', type=int)