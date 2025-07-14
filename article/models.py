from django.db import models

class Article(models.Model) :
    TAGS = (
        ("news", "ニュース"),
        ("release", "リリースノート"),
        ("howto", "使い方"),
        ("blog", "ブログ"),
        ("tool", "ツール"),
        ("other", "その他"),
    )
    article_id = models.CharField(default = "", max_length = 100, primary_key=True)
    title = models.CharField(default = "", max_length = 500)
    author = models.CharField(default = "", max_length = 50)
    tag = models.CharField(default = "", choices=TAGS, max_length=10)
    text = models.TextField(default = "", blank = True, null = True, max_length = 1000000)
    post_time = models.DateTimeField(blank = True, null = True)
    is_open = models.BooleanField(default = True)
    is_md = models.BooleanField(default = True)

    def __str__(self):
        return self.title