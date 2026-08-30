from django.views.generic.base import RedirectView
from django.urls import path, include, register_converter
from subekashi.converters import SQLiteIntConverter
from subekashi.views import *
from rest_framework import routers

app_name='subekashi'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', SongAPI)
defaultRouter.register('songlink', SongLinkAPI, basename='songlink')
defaultRouter.register('ai', AiAPI)
defaultRouter.register('ad', AdAPI)

register_converter(SQLiteIntConverter, 'sqliteint')

urlpatterns = [
    path('', TopView.as_view(), name='top'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('songs/', SongsView.as_view(), name='songs'),
    path('stats/', StatsView.as_view(), name='stats'),
    path('songs/new/', SongNewView.as_view(), name='song_new'),
    path('songs/<sqliteint:song_id>/', SongView.as_view(), name='song'),
    path('songs/<sqliteint:song_id>/edit/', SongEditView.as_view(), name='song_edit'),
    path('songs/<sqliteint:song_id>/history/', SongHistoryView.as_view(), name='song_history'),
    path('songs/<sqliteint:song_id>/delete/', SongDeleteView.as_view(), name='song_delete'),
    path('authors/<sqliteint:author_id>/', AuthorView.as_view(), name='author'),
    path('authors/<sqliteint:author_id>/stats/', AuthorStatsView.as_view(), name='author_stats'),
    path('authors/<sqliteint:author_id>/aliases/', AuthorAliasesView.as_view(), name='author_aliases'),
    path('authors/<sqliteint:author_id>/aliases/primary/', AuthorPrimaryNameSetView.as_view(), name='author_primary_name_set'),
    path('authors/<sqliteint:author_id>/aliases/primary/confirm/', AuthorPrimaryNameConfirmView.as_view(), name='author_primary_name_confirm'),
    path('authors/<sqliteint:author_id>/aliases/new/', AuthorAliasNewView.as_view(), name='author_alias_new'),
    path('authors/<sqliteint:author_id>/aliases/<sqliteint:alias_id>/edit/', AuthorAliasEditView.as_view(), name='author_alias_edit'),
    path('authors/<sqliteint:author_id>/aliases/<sqliteint:alias_id>/delete/', AuthorAliasDeleteView.as_view(), name='author_alias_delete'),
    path('editor/<sqliteint:editor_id>/', EditorView.as_view(), name='editor'),
    path('histories/', HistoriesView.as_view(), name='histories'),
    path('ai/', AiView.as_view(), name='ai'),
    path('ai/result/', AiResultView.as_view(), name='ai_result'),
    path('setting/', SettingView.as_view(), name='setting'),
    path('api/setting/save/', SaveSettingsView.as_view(), name='save_settings'),
    path('ad/', ad, name='ad'),
    path('ad/complete/', AdCompleteView.as_view(), name='ad_complete'),
    path('robots.txt', robots, name='robots'),
    path('sitemap.xml', sitemap, name='sitemap'),
    path('favicon.ico', favicon, name='favicon'),
    path('.well-known/traffic-advice', trafficAdvice, name='traffic-advice'),
    path('api/ai/swap/', AiWordSwapView.as_view(), name='ai-word-swap'),
    path('api/',include(defaultRouter.urls)),
    path('api/editor/is_open', EditorIsOpenView.as_view(), name='editor-is-open'),
    path('api/song_edit_init/', SongEditInitView.as_view(), name='song-edit-init'),
    path('api/word/candidates/', WordCandidatesView.as_view(), name='word-candidates'),
    path('api/html/song_cards', song_cards, name='song_cards'),
    path('api/html/song_guessers', song_guessers, name='song_guessers'),
    path('api/html/toast', toast, name='toast'),
    path('search/', RedirectView.as_view(url=f"/songs/", permanent=False)),
    path('new/', RedirectView.as_view(url='/songs/new/', permanent=False)),
    path('channel/<str:channel_name>/', ChannelView.as_view(), name='channel'),
]
