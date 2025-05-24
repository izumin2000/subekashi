from django.db import models


# TODO DBの見直し
class Song(models.Model) :
    title = models.CharField(default = "", max_length = 500)
    channel = models.CharField(default = "", max_length = 500)
    url = models.CharField(blank = True, null = True, default = "", max_length = 500)
    lyrics = models.TextField(blank = True, null = True, default = "", max_length = 10000)      
    imitate = models.CharField(blank = True, null = True, default = "", max_length = 10000)
    imitated = models.CharField(blank = True, null = True, default = "", max_length = 10000)
    post_time = models.DateTimeField()
    upload_time = models.DateTimeField(blank = True, null = True)
    isoriginal = models.BooleanField(default = False)
    isjoke = models.BooleanField(default = False)
    isdeleted = models.BooleanField(default = False)
    isdraft = models.BooleanField(default = False)
    isinst = models.BooleanField(default = False)
    issubeana = models.BooleanField(default = True)
    isarrange = models.BooleanField(default = False)
    isotomad = models.BooleanField(default = False)
    isnotice = models.BooleanField(default = False)
    isdec = models.BooleanField(default = False)
    isspecial = models.BooleanField(default = False)
    islock = models.BooleanField(default = False)
    ip = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(blank = True, null = True)
    like = models.IntegerField(blank = True, null = True)

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


class Contact(models.Model) :
    detail = models.TextField(max_length = 10000)
    post_time = models.DateField()
    answer = models.TextField(blank = True, null = True, max_length = 10000)
    
    def __str__(self) :
        return self.detail[:30]
    
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
    
class Article(models.Model) :
    tags = (
        ('news', 'ニュース'),
        ('release', 'リリースノート'),
        ('howto', '使い方'),
        ('blog', 'ブログ'),
    )
    article_id = models.CharField(default = "", max_length = 100, primary_key=True)
    title = models.CharField(default = "", max_length = 500)
    tag = models.CharField(default = "", choices=tags, max_length=10)
    text = models.CharField(default = "", blank = True, null = True, max_length = 500)
    post_time = models.DateTimeField(blank = True, null = True)
    is_open = models.BooleanField(default = True)
    is_md = models.BooleanField(default = True)

    def __str__(self):
        return self.title