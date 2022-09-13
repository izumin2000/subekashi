from statistics import mode
from django.db import models

# Create your models here.
class Channel(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)

    def __str__(self):
        return self.name


class Song(models.Model) :
    title = models.CharField(default = "", max_length = 100)
    lyrics = models.CharField(default = "", max_length = 10000)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)
    channel = models.ForeignKey("Channel", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "song_channel")
    imitate = models.ForeignKey("Song", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "song_imitate")

    def __str__(self):
        return self.title


class Word(models.Model) :
    song = models.ForeignKey("Song", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "word_song")
    title = models.CharField(default = "", max_length = 100)
    words = models.CharField(default = "", max_length = 10000)


class Ai(models.Model) :
    lyrics = models.CharField(default="", max_length = 50)
    isgood = models.BooleanField(default = False)
    
    def __str__(self):
        return self.lyrics