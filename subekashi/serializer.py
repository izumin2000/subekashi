from rest_framework import serializers
from .models import *

class SongSerializer(serializers.ModelSerializer):
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