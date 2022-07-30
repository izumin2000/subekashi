from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('subeana/', include('subeana.urls')),
    path('xia/', include('xia.urls')),
]