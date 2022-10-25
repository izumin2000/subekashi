from django.db import models

# Create your models here.
class Info(models.Model) :
    name = models.CharField(default = "", max_length = 10)
    value = models.CharField(default = "", max_length = 10)