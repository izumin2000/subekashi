"""
ASGI config for izuminapp project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os
from django import http

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter
from channels.routing import URLRouter
from izuminapp.routing import ws_urlpatterns


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'izuminapp.settings')

application = ProtocolTypeRouter({
    'http' : get_asgi_application(),
    'websoket': AuthMiddlewareStack(URLRouter(ws_urlpatterns))
})
