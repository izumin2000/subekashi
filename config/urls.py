from django.contrib import admin
from django.urls import path, include
from subekashi import views
from django.conf.urls import handler500, handler404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("subekashi.urls")),
]


handler404 = views.handle_404_error
handler500 = views.handle_500_error