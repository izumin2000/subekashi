from subekashi.lib.security import decrypt
from subekashi.models import Song
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "暗号化されたIPアドレスを復号化"

    def add_arguments(self, parser):
        parser.add_argument("-id", type=int, help="Song ID")
    
    def handle(self, *args, **options) :
        song_id = options["id"]
        song = Song.objects.get(pk=song_id)
        decrypted_ip = decrypt(song.ip)
        self.stdout.write(self.style.SUCCESS(decrypted_ip))
        