from django.apps import AppConfig


class subekashiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subekashi'

    def ready(self):
        from subekashi.lib.db_lookups import register
        register()
