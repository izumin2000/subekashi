from django.db import models

class Oldjson(models.Model) :
    nations = models.CharField(default = "", max_length = 1000)

class Player(models.Model) :
    name = models.CharField(default = "", max_length = 100)
    info = models.CharField(default = "", max_length = 1000)
    online = models.BooleanField(default = False)

class Firstview(models.Model) :
    images = models.ImageField(upload_to='', null=True, blank=True)
    title = models.CharField(default = "", max_length = 100)
    player = models.CharField(default = "", max_length = 100)
    display = models.BooleanField(default = False)