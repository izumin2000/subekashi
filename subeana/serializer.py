from dataclasses import fields
from pyexpat import model
from rest_framework import serializers
from .models import Song

class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = '__all__'
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)