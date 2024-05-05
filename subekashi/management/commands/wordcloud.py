from django.core.management.base import BaseCommand
from subekashi.models import *
from wordcloud import WordCloud

class Command(BaseCommand) :
    def handle(self, *args, **options):
        
        songs = Song.objects.filter(isjoke = False, issubeana = True)
        lyrics = ""
        for song in songs:
            lyrics += song.lyrics if song.lyrics else ""
        
        wordcloud = WordCloud(
                font_path=r"C:\Users\kanat\AppData\Local\Microsoft\Windows\Fonts\GenZenGothicKaiC.ttf",
                collocations = False,
                max_words = 6000,
                regexp=r"[\w']+",
                stopwords = [],
                colormap="summer_r",
                width=8000,height=4500).generate(lyrics)

        wordcloud.to_file(r"C:\Users\kanat\Documents\codes\subekashi\subekashi\words.jpeg")
        
        
