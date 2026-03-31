from django.db import models
from .song import Song


# 曲のURLの情報
class SongLink(models.Model):
    url = models.URLField(max_length=500, unique=True)
    songs = models.ManyToManyField(Song, blank=True, related_name='links')
    is_removed = models.BooleanField(default=False)
    allow_dup = models.BooleanField(default=False)

    def __str__(self):
        return self.url
