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
    # imitateds は逆参照のため明示的に宣言（__all__に含まれない）
    imitateds = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    def get_url(self, obj):
        return list(obj.links.values_list('url', flat=True))

    class Meta:
        model = Song
        fields = '__all__'


class SongLinkSongSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    is_lack = serializers.SerializerMethodField()

    def get_is_lack(self, obj):
        # SongLinkAPIのクエリセットでannotateされたis_lackを優先使用（N+1回避）
        if hasattr(obj, 'is_lack'):
            return obj.is_lack
        from subekashi.lib.query_filters import filter_by_lack
        return Song.objects.filter(pk=obj.pk).filter(filter_by_lack()).exists()

    class Meta:
        model = Song
        fields = ['id', 'title', 'authors', 'is_lack']


class SongLinkSerializer(serializers.ModelSerializer):
    songs = SongLinkSongSerializer(many=True, read_only=True)

    class Meta:
        model = SongLink
        fields = ['id', 'url', 'is_removed', 'allow_dup', 'songs']


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