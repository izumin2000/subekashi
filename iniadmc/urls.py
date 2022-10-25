from django.contrib import admin
from . import views
from django.urls import path, include
from rest_framework import routers

app_name = 'iniadmc'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('Wait', views.WaitViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name = 'top'),
    path('change', views.change, name = 'change'),
    path('api/',include(defaultRouter.urls)),
]