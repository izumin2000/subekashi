from rest_framework import serializers
from .models import Users

class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = '__all__'
    
    def get_default(self):
        return super().get_default()
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
        # return super().update(instance, validated_data)