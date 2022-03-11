from django.db import models

class Player(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    uuid = models.CharField(default = "", max_length = 50)
    info = models.CharField(default = "", max_length = 200)
    rank = models.CharField(default = "国民", max_length = 20)
    online = models.BooleanField(default = False)
    primary = models.BooleanField(default = False)
    leave = models.BooleanField(default = False)
    crime = models.BooleanField(default = False)

class Firstview(models.Model) :
    image = models.CharField(default = "", max_length = 100)
    title = models.CharField(default = "", max_length = 20)
    player = models.CharField(default = "", max_length = 20)

# シングルトン
class Singleton(models.Model) :
    name = models.CharField(default = "", max_length = 20)
    value = models.CharField(default = "", max_length = 10000)

class Analyze(models.Model) :
    date = models.DateField(null = True, blank = True)
    pv = models.IntegerField(default = 0)