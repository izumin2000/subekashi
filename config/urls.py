from django.contrib import admin
from django.urls import path, include
from subekashi.views import errors
from django.conf.urls import handler500, handler404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("subekashi.urls")),
]

handler404 = errors.handle_404_error
handler500 = errors.handle_500_error