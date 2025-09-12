from django.contrib import admin
from .models import *


class SongAdmin(admin.ModelAdmin):
    fields = ["title", "channel", "url", "imitate", "imitated", "lyrics", "view", "like", "post_time", "upload_time", "isoriginal", "isjoke", "issubeana", "isdeleted", "isinst", "isdraft", "isspecial", "islock"]

admin.site.register(Song, SongAdmin)


class ContentAdmin(admin.ModelAdmin):
    fields = ["detail", "post_time", "answer"]
    
admin.site.register(Contact, ContentAdmin)


class HistoryAdmin(admin.ModelAdmin):
    fields = [field.name for field in History._meta.get_fields()].remove("id")
    
admin.site.register(History, HistoryAdmin)


# TODO Unknown field(s) (songs, histories) specified for Editor. Check fields/fieldsets/exclude attributes of class EditorAdmin.エラーの修正
# class EditorAdmin(admin.ModelAdmin):
    # fields = [field.name for field in Editor._meta.get_fields()]
    # 
# admin.site.register(Editor, EditorAdmin)