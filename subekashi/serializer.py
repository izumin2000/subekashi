from rest_framework import serializers
from .models import *

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name']

class SongSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)

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