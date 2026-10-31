from django.contrib import admin
from .models import *


class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_removed')
    search_fields = ('title',)
    # ユーザーが削除した曲（#1239）も表示し、is_removedのチェックを外して復元できるようにする
    list_filter = ('is_removed',)

    def get_queryset(self, request):
        return Song.all_objects.all()

admin.site.register(Song, SongAdmin)


class ContentAdmin(admin.ModelAdmin):
    pass
    
admin.site.register(Contact, ContentAdmin)


class EditorAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_open', 'is_forced_open', 'is_banned')
    list_filter = ('is_banned',)

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


class SongLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'is_removed', 'allow_dup')
    search_fields = ('url', 'songs__title')
    list_filter = ('is_removed', 'allow_dup')

admin.site.register(SongLink, SongLinkAdmin)


class StatsAdmin(admin.ModelAdmin):
    list_display = ('id', 'year', 'month', 'songrange', 'song_count', 'total_view', 'total_like', 'total_authors', 'total_imitated_authors', 'total_imitateds')
    list_filter = ('songrange',)
    ordering = ('-year', '-month', 'songrange')

admin.site.register(Stats, StatsAdmin)


class PrushAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date')
    search_fields = ('name',)

admin.site.register(Prush, PrushAdmin)


class SongTimelineAdmin(admin.ModelAdmin):
    list_display = ('id', 'song', 'year', 'row', 'is_lyrics_blank')
    list_filter = ('year', 'is_lyrics_blank')
    # 曲の選択肢が約14000件になるため、セレクトボックスではなくidで指定する
    raw_id_fields = ('song',)

admin.site.register(SongTimeline, SongTimelineAdmin)
