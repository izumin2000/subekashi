from rest_framework import serializers
from .models import *

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name']

class SongSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    # Song.urlフィールドの代わりにSongLinkテーブルから取得したURLリストを返す
    # レスポンス形式: "url": ["https://youtu.be/...", ...]
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return list(obj.links.filter(is_removed=False).values_list('url', flat=True))

    class Meta:
        model = Song
        fields = '__all__'


class AiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ai
        fields = '__all__'

    
class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = '__all__'


class IsOpenSerializer(serializers.Serializer):
    ip = serializers.CharField()
    is_open = serializers.BooleanField(required=False)