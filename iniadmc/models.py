from django.db import models

class Wait(models.Model) :
    minutes = models.IntegerField(default = 0)