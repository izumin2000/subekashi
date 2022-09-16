from statistics import mode
from django.db import models


class Channel(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)

    def __str__(self):
        return self.name


class Song(models.Model) :
    title = models.CharField(default = "", max_length = 100)
    channel = models.CharField(default = "", max_length = 50)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)
    lyrics = models.CharField(default = "", max_length = 10000)
    imitate = models.CharField(default = "", max_length = 1000)

    def __str__(self):
        return self.title


class Word(models.Model) :
    song = models.OneToOneField("Song", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "word_song")
    title = models.CharField(default = "", max_length = 100)
    words = models.CharField(default = "", max_length = 10000)


class Ai(models.Model) :
    lyrics = models.CharField(default="", max_length = 50)
    isgood = models.BooleanField(default = False)
    
    def __str__(self):
        return self.lyrics