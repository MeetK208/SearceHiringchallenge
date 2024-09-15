from django.db import models
from register.models import User

class Project(models.Model):
    projectName = models.CharField(max_length=255)
    projectDesc = models.TextField()
    projectId = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')  # Owner of the project
    totalPosition = models.IntegerField()
    budget = models.CharField(max_length=20)
    role = models.CharField(max_length=50, default='user')  # Default role is 'user'
    last_edited_by_userId = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='edited_projects')  # Last user who edited
    last_updated_timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.projectName + " " + str(self.projectId)

class ProjectUser(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE)  # ForeignKey to User model
    projectId = models.ForeignKey(Project, on_delete=models.CASCADE)  # ForeignKey to Project model
    is_owner = models.BooleanField(default=False)
    def __str__(self):
        return f"User {self.userId} - Project {self.projectId} - is Owner {self.is_owner}"
