from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('emctour/', views.emctour, name = 'emctour'),
    path('', views.root, name = 'root'),
    path('inca/', views.inca, name = 'inca'),
    path('inca/pv', views.pv, name = 'pv'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
    
    # path('inca/firstview', views.firstview, name = 'firstview'),
    # path('inca/editplayer', views.editplayer, name = 'editplayer'),