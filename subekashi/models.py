from django.db import models


# TODO 要リファクタリング
class Song(models.Model) :
    title = models.CharField(default = "", max_length = 500)
    channel = models.CharField(default = "", max_length = 500)
    url = models.CharField(default = "", max_length = 500, blank = True, null = True)
    lyrics = models.CharField(default = "", max_length = 10000, blank = True, null = True)
    imitate = models.CharField(default = "", max_length = 1000, blank = True, null = True)
    imitated = models.CharField(default = "", max_length = 1000, blank = True, null = True)
    post_time = models.DateTimeField(blank = True, null = True)     # TODO null成約を消す
    upload_time = models.DateField(blank = True, null = True)
    isoriginal = models.BooleanField(default = False)
    isjoke = models.BooleanField(default = False)
    isdeleted = models.BooleanField(default = False)
    isarchived = models.BooleanField(default = True)
    isdraft = models.BooleanField(default = False)
    isinst = models.BooleanField(default = False)
    issubeana = models.BooleanField(default = True)
    ip = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(default = 0)
    like = models.IntegerField(default = 0)

    def __str__(self) :
        return self.title


class Channel(models.Model) :
    name = models.CharField(default = "", max_length = 100)
    ismain = models.BooleanField(default = True)
    isnickname = models.BooleanField(default = True)
    subs = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='main')

    def __str__(self) :
        return self.name
    

class Version(models.Model) :
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    before = models.CharField(default = "", max_length = 10000)
    after = models.CharField(default = "", max_length = 10000)
    editedtime = models.DateTimeField(blank = True, null = True)
    ip = models.CharField(default = "", max_length = 100)

class Ai(models.Model) :
    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)
    
    def __str__(self):
        return self.lyrics


class Ad(models.Model) :
    choices = (
        ('still', '未審査'),
        ('pass', '公開中'),
        ('fail', '未通過'),
    )
    url = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(default = 0)
    click = models.IntegerField(default = 0)
    dup = models.IntegerField(default = 0)
    status = models.CharField(default = "still", choices=choices, max_length=10)
    
    def __str__(self):
        return self.url