from django.contrib import admin
from django.urls import path
from . import views

app_name = 'inca'

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.inca, name = 'inca'),
    path('nations', views.emctour, name = 'emctour'),
    path('nations/<str:nation>', views.nation, name = 'nation'),
    path('nations/modarticle/<str:nation>', views.modarticle, name = 'modarticle'),
    path('nations/list/<str:order>', views.nationlist, name = 'nationlist'),
    path('pv', views.pv, name = 'pv'),
]

    # path('firstview', views.firstview, name = 'firstview'),
    # path('editplayer', views.editplayer, name = 'editplayer'),