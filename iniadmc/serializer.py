from dataclasses import fields
from rest_framework import serializers
from .models import Wait

class WaitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wait
        fields = ('minutes',)