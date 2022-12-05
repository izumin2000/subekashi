from django.db import models


class Song(models.Model) :
    title = models.CharField(default = "", max_length = 100)
    channel = models.CharField(default = "", max_length = 50)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)
    lyrics = models.CharField(default = "", max_length = 10000, blank = True, null = True)
    ruigo = models.CharField(default = "", max_length = 10000, blank = True, null = True)
    imitate = models.CharField(default = "", max_length = 1000)
    imitated = models.CharField(default = "", max_length = 1000)
    isjoke = models.BooleanField(default = False)
    isjapanese = models.BooleanField(default = True)

    def __str__(self):
        return self.title


class Ai(models.Model) :
    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    people = models.IntegerField(default = 0)
    users = models.CharField(default = "", max_length = 1000)
    genetype = models.CharField(default = "", max_length = 100)
    category = models.CharField(default = "", max_length = 100)
    title = models.CharField(default = "", max_length = 100)
    similar = models.CharField(default = "", max_length = 100)
    isgpt = models.BooleanField(default = False)
    
    def __str__(self):
        return self.lyrics
