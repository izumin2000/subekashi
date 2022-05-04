from django.db import models

class Player(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    nickname = models.CharField(default = "", max_length = 50)
    uuid = models.CharField(default = "", max_length = 50)
    town = models.ForeignKey("Town", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "player_town")
    nation = models.ForeignKey("Nation", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "player_nation")
    info = models.CharField(default = "", max_length = 200)
    online = models.BooleanField(default = False)
    goldsam = models.IntegerField(default = 0)

class Citizen(models.Model) :
    player = models.ForeignKey("Player", on_delete = models.DO_NOTHING, blank = True, null = True)
    iscitizen = models.BooleanField(default = True)

class Minister(models.Model) :
    citizen = models.ForeignKey("Citizen", on_delete = models.DO_NOTHING, blank = True, null = True)
    title = models.CharField(default = "大臣", max_length = 20)
    isminister = models.BooleanField(default = True)

class Criminal(models.Model) :
    player = models.ForeignKey("Player", on_delete = models.CASCADE)
    info = models.CharField(default = "", max_length = 20)
    x = models.IntegerField(default = 0)
    z = models.IntegerField(default = 0)
    isunderground = models.BooleanField(default = True)

class Gold(models.Model) :
    player = models.ForeignKey("Player", on_delete = models.CASCADE)
    date = models.DateField(blank = True, null = True)
    amount = models.IntegerField(default = 0)

class Tour(models.Model) :
    nation = models.ForeignKey("Nation", on_delete = models.DO_NOTHING, blank = True, null = True)
    info = models.CharField(default = "", max_length = 500)
    

class Town(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    nickname = models.CharField(default = "", max_length = 50)
    population = models.IntegerField(default = 0)
    area = models.IntegerField(default = 0)
    x = models.IntegerField(default = 0)
    z = models.IntegerField(default = 0)
    info = models.CharField(default = "", max_length = 200)
    mayor = models.ForeignKey("Player", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "town_mayor")

class Nation(models.Model) :
    name = models.CharField(default = "", max_length = 50)
    nickname = models.CharField(default = "", max_length = 50)
    population = models.IntegerField(default = 0)
    area = models.IntegerField(default = 0)
    capital = models.ForeignKey("Town", on_delete = models.DO_NOTHING, blank = True, null = True)
    x = models.IntegerField(default = 0)
    z = models.IntegerField(default = 0)
    info = models.CharField(default = "", max_length = 200)
    king = models.ForeignKey("Player", on_delete = models.DO_NOTHING, blank = True, null = True, related_name = "nation_king")

class Firstview(models.Model) :
    name = models.CharField(default = "", max_length = 100)
    title = models.CharField(default = "無題", max_length = 20)
    display = models.BooleanField(default = True)

class Analyze(models.Model) :
    date = models.DateField(null = True, blank = True)
    pv = models.IntegerField(default = 0)