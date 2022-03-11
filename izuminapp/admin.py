from django.contrib import admin
from izuminapp.model import Player, Firstview, Singleton, Analyze


class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rank", "online", "leave", "crime", "uuid", "info")
    list_display_links = ("id", "name")
    ordering = ("id", )

class FirstviewAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "title", "player")
    list_display_links = ("id", "image")
    ordering = ("id", )

class SingletonAdmin(admin.ModelAdmin):
    list_display  = ("name", "value")
    list_display_links = ("name", )

class AnalyzeAdmin(admin.ModelAdmin):
    list_display  = ("date", "pv")
    list_display_links = ("date", )
    ordering = ("id", )


admin.site.register(Player, PlayerAdmin)
admin.site.register(Firstview, FirstviewAdmin)
admin.site.register(Singleton, SingletonAdmin)
admin.site.register(Analyze, AnalyzeAdmin)