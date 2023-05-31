from django.db import models

class Users(models.Model) :
    user_id = models.CharField(default = "", max_length = 20, primary_key=True)
    password = models.CharField(default = "", max_length = 20)
    nickname = models.CharField(default = "", max_length = 30)
    comment = models.CharField(default = "", max_length = 100)