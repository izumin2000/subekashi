from django.contrib import admin
from django.urls import path, include
from subekashi.views import errors
from django.conf.urls import handler500, handler404
from django.conf.urls.static import static
from django.urls import path
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("subekashi.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = errors.handle_404_error
handler500 = errors.handle_500_error