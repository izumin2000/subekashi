from django.db import models
from .song import Song


# 曲のURLの情報
class SongLink(models.Model):
    # 一意性はDBレベルでは保証されない（Author.nameと同様の理由。#1092参照）。
    # 実際の一意制約はsubekashi/migrations/0050_mysql_case_insensitive_search.py側にある
    url = models.URLField(max_length=255)
    songs = models.ManyToManyField(Song, blank=True, related_name='links')
    is_removed = models.BooleanField(default=False)
    allow_dup = models.BooleanField(default=False)

    def __str__(self):
        return self.url

    @classmethod
    def set_allow_dup_for_url(cls, url):
        """指定URLのSongLinkのallow_dup=Trueに設定する"""
        link = cls.objects.filter(url__iexact=url).first()
        if link:
            link.allow_dup = True
            link.save()
        return link
