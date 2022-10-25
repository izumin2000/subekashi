from django.db import models

class Wait(models.Model) :
    minutes = models.IntegerField(default = 0, max_length = 1000)