from django.core.management.base import BaseCommand
from subekashi.models import *

class Command(BaseCommand) :
    def handle(self, *args, **options):
        songs_with_numbers = Song.objects.filter(title__regex=r'\d')
        song_list = list(songs_with_numbers.values_list('id', 'title'))
        song_list = [f"{id} {title}" for id, title in song_list]
        print("\n".join(song_list))
