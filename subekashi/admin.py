from django.contrib import admin

from .models import *


class SongAdmin(admin.ModelAdmin):
    fields = ["title", "channel", "url", "imitate", "imitated", "lyrics", "isoriginal", "isjoke", "issubeana", "isdeleted", "isinst", "isarchived", "isdraft"]

admin.site.register(Song, SongAdmin)

class ContentAdmin(admin.ModelAdmin):
    fields = ["detail", "post_time", "answer"]
    
admin.site.register(Contact, ContentAdmin)