from django.urls import path
from .consumers import WSConsumer

ws_urlpatterns = {
    path('ws/izuminapp', WSConsumer.as_asgi())
}