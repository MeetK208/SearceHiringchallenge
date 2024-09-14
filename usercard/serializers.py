from rest_framework import serializers
from .models import *
class ProjectCardUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCardUser
        # feild = ['email','role']
        # exclude = ['password',]
        fields = '__all__'
        extra_kwargs = {
            'designation': {'required': True},
            'department': {'required': True},
            'budget': {'required': False},  # AutoField doesn't need to be provided manually
            'location': {'required': True}  # Even though there's a default, you can still make it required
        }
