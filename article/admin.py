from django.contrib import admin
from .models import Article


class ArticleAdmin(admin.ModelAdmin):
    fields = [field.name for field in Article._meta.get_fields()]
    
admin.site.register(Article, ArticleAdmin)