from rest_framework import serializers
from .models import *
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # feild = ['email','role']
        # exclude = ['password',]
        fields = '__all__'
        extra_kwargs = {
            'email': {'required': True},
            'password': {'required': True},
            'userId': {'required': False},  # AutoField doesn't need to be provided manually
            'role': {'required': True}  # Even though there's a default, you can still make it required
        }
