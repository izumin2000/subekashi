from django.contrib import admin

from .models import Song


class SongAdmin(admin.ModelAdmin):
    fields = ["title", "channel", "url", "imitate", "imitated", "lyrics", "isoriginal", "isjoke", "issubeana", "isdeleted", "isinst", "isarchived", "isdraft"]

admin.site.register(Song, SongAdmin)
