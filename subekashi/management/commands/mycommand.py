from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand) :
    def handle(self, *args, **options):
        songRec = Song.objects.get(id = options["id"])
        