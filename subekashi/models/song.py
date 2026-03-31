from django.db import models
from django.utils import timezone
from .author import Author


# 楽曲のメイン情報
class Song(models.Model):
    CHOICES = (
        ("song", "曲"),
        ("arrange", "アレンジ"),
        ("otomad", "音MAD"),
        ("medley", "メドレー"),
        ("omnibus", "総集編"),
        ("notice", "告知"),
        ("dec", "解読"),
        ("offv", "オフボ"),
        ("cover", "カバー"),
        ("joke", "ネタ動画"),
        ("other", "その他"),
    )

    title = models.CharField(default = "", max_length = 500)
    authors = models.ManyToManyField(Author, related_name='songs', blank=True)
    lyrics = models.TextField(blank = True, null = True, default = "", max_length = 10000)
    imitates = models.ManyToManyField("self", symmetrical=False, related_name="imitateds", blank=True)
    post_time = models.DateTimeField(default = timezone.now)
    upload_time = models.DateTimeField(blank = True, null = True)
    is_original = models.BooleanField(default = False)
    is_joke = models.BooleanField(default = False)
    is_deleted = models.BooleanField(default = False)
    is_draft = models.BooleanField(default = False)
    is_inst = models.BooleanField(default = False)
    is_subeana = models.BooleanField(default = True)
    is_special = models.BooleanField(default = False)
    is_lock = models.BooleanField(default = False)
    is_limited = models.BooleanField(default = False)
    view = models.IntegerField(blank = True, null = True)
    like = models.IntegerField(blank = True, null = True)
    category = models.CharField(default = "song", choices=CHOICES, max_length=10)

    def __str__(self):
        return self.title

    def authors_str(self, separator=", "):
        """作者をカンマ区切りの文字列で返す"""
        author_names = [author.name for author in self.authors.all()]
        return separator.join(author_names)

    def save(self, *args, **kwargs):
        if self.lyrics:
            self.lyrics = self.lyrics.replace("\r\n", "\n")
        super().save(*args, **kwargs)
