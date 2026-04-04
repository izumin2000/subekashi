from dataclasses import make_dataclass, field as dc_field
from django.db import models
from django.db.models.fields import NOT_PROVIDED as _NOT_PROVIDED
from django.db.models.query_utils import DeferredAttribute
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

    @classmethod
    def get_or_none(cls, pk):
        try:
            return cls.objects.get(pk=pk)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_for_range(cls, songrange, jokerange):
        """songrange/jokerangeの設定に応じたQuerySetを返す"""
        if songrange == "subeana":
            qs = cls.objects.filter(is_subeana=True)
        elif songrange == "xx":
            qs = cls.objects.filter(is_subeana=False)
        else:
            qs = cls.objects.all()
        if jokerange == "off":
            qs = qs.filter(is_joke=False)
        return qs

    @classmethod
    def get_for_author(cls, author_id):
        """指定author_idに紐づくSongのQuerySetを返す"""
        return cls.objects.filter(authors__id=author_id).distinct().order_by('-id')

    @classmethod
    def is_lack(cls, pk):
        """指定pkのSongが未完成かどうかを返す"""
        from subekashi.lib.query_filters import filter_by_lack
        return cls.objects.filter(pk=pk).filter(filter_by_lack()).exists()

    def has_subekashi_author(self):
        """Songにid=1（すべあな）作者が紐づいているかを返す"""
        return self.authors.filter(id=1).exists()


# Songモデルのフォームフィールドをまとめるデータクラス。
# Song.__dict__からDeferredAttributeを持つフィールドを自動検出し、
# システム管理フィールドのみを除外リストで管理する。
_SONG_FIELDS_EXCLUDE = {'id', 'post_time', 'category', 'is_special', 'is_lock', 'is_limited'}


def _build_song_fields():
    specs = []
    for name, descriptor in Song.__dict__.items():
        if not isinstance(descriptor, DeferredAttribute):
            continue
        if name in _SONG_FIELDS_EXCLUDE:
            continue
        default = Song._meta.get_field(name).default
        if default is _NOT_PROVIDED:
            specs.append((name, object, dc_field(default=None)))
        else:
            specs.append((name, type(default), dc_field(default=default)))
    return make_dataclass('SongFields', specs)


SongFields = _build_song_fields()
