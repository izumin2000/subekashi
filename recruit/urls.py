from django.contrib import admin
from . import views
from django.urls import path,include
from rest_framework import routers


app_name = 'recruit'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('users', views.UsersViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', include(defaultRouter.urls)),
    path('signup', views.signup, name='signup'),
    path('close', views.close, name='close'),
]