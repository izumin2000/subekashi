from django.contrib import admin
from izuminapp.model import Player, Citizen, Minister, Criminal, Gold, Tour, Town, Nation, Firstview, Analyze


class PlayerAdmin(admin.ModelAdmin) :
    list_display = ["id", "name", "nickname", "nation", "town", "online", "goldsam"]
    list_display_links = ["id", "name"]
    ordering = ["id"]
    def nation(self, obj) :
        return obj.nation.name
    def town(self, obj) :
        return obj.town.name

class CitizenAdmin(admin.ModelAdmin) :
    list_display = ["player", "iscitizen"]
    list_display_links = ["player"]
    ordering = ["player"]
    def player(self, obj) :
        return obj.player.name

class MinisterAdmin(admin.ModelAdmin) :
    list_display = ["citizen", "title", "isminister"]
    list_display_links = ["citizen"]
    ordering = ["citizen"]
    def citizen(self, obj) :
        return obj.citizen.player.name

class CriminalAdmin(admin.ModelAdmin) :
    list_display = ["player", "info", "x", "z", "isunderground"]
    list_display_links = ["player"]
    ordering = ["player"]
    def player(self, obj) :
        return obj.player.name

class GoldAdmin(admin.ModelAdmin) :
    list_display = ["player", "date", "amount"]
    list_display_links = ["player"]
    ordering = ["player"]
    def player(self, obj) :
        return obj.player.name

class TourAdmin(admin.ModelAdmin) :
    list_display = ["nation", "info"]
    list_display_links = ["nation"]
    ordering = ["nation"]
    def nation(self, obj) :
        return obj.nation.name

class TownAdmin(admin.ModelAdmin) :
    list_display = ["name", "nickname", "population", "area", "x", "z", "info", "mayor"]
    list_display_links = ["name", "nickname"]
    ordering = ["name"]
    def mayor(self, obj) :
        return obj.mayor.name

class NationAdmin(admin.ModelAdmin) :
    list_display = ["name", "nickname", "population", "area", "capital", "x", "z", "info", "king"]
    list_display_links = ["name", "nickname"]
    ordering = ["name"]
    def capital(self, obj) :
        return obj.capital.name

class FirstviewAdmin(admin.ModelAdmin) :
    list_display = ["id", "name", "title", "display"]
    list_display_links = ["id", "name"]
    ordering = ["id"]

class AnalyzeAdmin(admin.ModelAdmin) :
    list_display = ["date", "pv"]
    list_display_links = ["date"]
    ordering = ["id"]

# Citizen, Minister, Criminal, Gold, Tour, Town, Nation,
admin.site.register(Player, PlayerAdmin)
admin.site.register(Citizen, CitizenAdmin)
admin.site.register(Minister, MinisterAdmin)
admin.site.register(Criminal, CriminalAdmin)
admin.site.register(Gold, GoldAdmin)
admin.site.register(Tour, TourAdmin)
admin.site.register(Town, TourAdmin)
admin.site.register(Nation, NationAdmin)
admin.site.register(Firstview, FirstviewAdmin)
admin.site.register(Analyze, AnalyzeAdmin)

"""
class Admin(admin.ModelAdmin) :
    list_display = [""]
    list_display_links = ["id"]
    ordering = ["id"]
"""