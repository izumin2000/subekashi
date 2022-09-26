from django.contrib import admin
from django.urls import path
from . import views

app_name = 'xia'

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name = 'top'),
    path('pv', views.pv, name = 'pv'),
    path('edit/player', views.editplayer, name = 'editplayer'),
    path('edit/player/delete/<int:player_id>', views.editplayerdelete, name = 'editplayerdelete'),
    path('edit/player/force/<str:name>', views.editplayerforce, name = 'editplayerforce'),
    path('edit/minister', views.editminister, name = 'editminister'),
    path('edit/minister/delete/<int:minister_id>', views.editministerdelete, name = 'editministerdelete'),
    path('edit/minister/force/<str:name>', views.editministerforce, name = 'editministerforce'),
    path('raid', views.raid, name = 'raid'),
]