from django.db import models


class Song(models.Model) :
    title = models.CharField(default = "", max_length = 100)
    channel = models.CharField(default = "", max_length = 50)
    url = models.CharField(default = "", max_length = 50, blank = True, null = True)
    lyrics = models.CharField(default = "", max_length = 10000, blank = True, null = True)
    ruigo = models.CharField(default = "", max_length = 10000, blank = True, null = True)
    imitate = models.CharField(default = "", max_length = 1000, blank = True, null = True)
    imitated = models.CharField(default = "", max_length = 1000, blank = True, null = True)
    isoriginal = models.BooleanField(default = False)
    isjoke = models.BooleanField(default = False)
    isjapanese = models.BooleanField(default = True)

    def __str__(self):
        return self.title


class Ai(models.Model) :
    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)
    
    def __str__(self):
        return self.lyrics


class Genecategory(models.Model) :
    ai = models.ForeignKey("Ai", on_delete = models.CASCADE, blank = True, null = True)
    category = models.CharField(default = "", max_length = 100)


class Genesong(models.Model) :
    ai = models.ForeignKey("Ai", on_delete = models.CASCADE, blank = True, null = True)
    title = models.CharField(default = "", max_length = 100)
    similar = models.CharField(default = "", max_length = 100)