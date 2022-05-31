from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('inca/', include('inca.urls')),
    path('subeana/', include('subeana.urls')),
]