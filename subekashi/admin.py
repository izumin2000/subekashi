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


class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('id',)

admin.site.register(Author, AuthorAdmin)


class AuthorAliasAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'alias_type')
    search_fields = ('name', 'author__name')
    list_filter = ('alias_type',)

admin.site.register(AuthorAlias, AuthorAliasAdmin)


class AuthorLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'url')
    search_fields = ('author__name', 'url')

admin.site.register(AuthorLink, AuthorLinkAdmin)