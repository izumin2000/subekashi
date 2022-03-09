from django.contrib import admin
from izuminapp.model import Player, Firstview, Siteinfo


class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rank", "online", "leave", "uuid", "info")
    list_display_links = ("id", "name")
    ordering = ("id", )

class FirstviewAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "title", "player")
    list_display_links = ("id", "image")
    ordering = ("id", )

class SiteinfoAdmin(admin.ModelAdmin):
    list_display  = ("date", "visit", "nations")
    list_display_links = ("date", "visit", "nations")


admin.site.register(Player, PlayerAdmin)
admin.site.register(Firstview, FirstviewAdmin)
admin.site.register(Siteinfo, SiteinfoAdmin)