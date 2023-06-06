from rest_framework import serializers
from .models import Song, Ai

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = ("id", "title", "channel", "url", "imitate", "imitated", "isoriginal", "isjoke", "isjapanese", "isdraft")
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class AiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ai
        fields = '__all__'
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)