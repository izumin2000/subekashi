from django.db import models

class Player(models.Model) :
    name = models.CharField(default = "", max_length = 100)
    uuid = models.CharField(default = "", max_length = 100)
    info = models.CharField(default = "", max_length = 1000)
    online = models.BooleanField(default = False)
    primary = models.BooleanField(default = False)
    leave = models.BooleanField(default = False)

class Firstview(models.Model) :
    image = models.ImageField(upload_to='', null = True, blank = True)
    title = models.CharField(default = "", max_length = 100)
    player = models.CharField(default = "", max_length = 100)

# シングルトン
class Siteinfo(models.Model) :
    date = models.DateField(null = True, blank = True)
    visit = models.IntegerField(default = 0)
    nations = models.CharField(default = "", max_length = 1000)