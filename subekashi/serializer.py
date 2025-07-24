from rest_framework import serializers
from .models import *

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = '__all__'
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class AiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ai
        fields = '__all__'
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = '__all__'
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)