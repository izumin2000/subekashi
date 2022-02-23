from django.db import models

class Oldjson(models.Model) :
    nations = models.CharField(default = "")
    players = models.CharField(default = "")

class Player(models.Model) :
    name = models.CharField(default = "")
    info = models.CharField(default = "")
    online = models.NullBooleanField(default = False)