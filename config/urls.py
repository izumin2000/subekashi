from django.contrib import admin
from django.urls import path, include
from subekashi import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.top, name = 'top'),
]