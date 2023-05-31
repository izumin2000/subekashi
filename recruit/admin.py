from django.contrib import admin

from .models import Users


class UsersAdmin(admin.ModelAdmin):
    fields = ("user_id", "password", "nickname", "comment")

admin.site.register(Users, UsersAdmin)