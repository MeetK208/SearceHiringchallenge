from rest_framework import serializers
from .models import Project, ProjectUser
from register.models import User

class ProjectUserSerializer(serializers.ModelSerializer):
    userId = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    projectId = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = ProjectUser
        fields = '__all__'
        extra_kwargs = {
            'projectId': {'required': True},
            'userId': {'required': True},
        }

class ProjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Owner of the project
    collaborators = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'
        extra_kwargs = {
            'projectName': {'required': True},
            'projectDesc': {'required': True},
            'user': {'required': True},
            'totalPosition': {'required': True},
            'role': {'required': True}
        }

    def get_collaborators(self, obj):
        # Retrieve the collaborators related to the project
        collaborators = ProjectUser.objects.filter(projectId=obj)
        return ProjectUserSerializer(collaborators, many=True).data
