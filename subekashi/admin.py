from django.contrib import admin
from .models import *


class SongAdmin(admin.ModelAdmin):
    pass

admin.site.register(Song, SongAdmin)


class ContentAdmin(admin.ModelAdmin):
    pass
    
admin.site.register(Contact, ContentAdmin)


class EditorAdmin(admin.ModelAdmin):
    pass

admin.site.register(Editor, EditorAdmin)


class HistoryAdmin(admin.ModelAdmin):
    pass
    
admin.site.register(History, HistoryAdmin)