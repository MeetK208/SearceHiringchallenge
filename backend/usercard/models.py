from django.db import models
from projectcard.models import *
from register.models import *
class ProjectCardUser(models.Model):
    projectCard = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='owned_projects')  # Correct foreign key reference
    carduserId = models.AutoField(primary_key=True)
    designation = models.CharField(max_length=50)
    department = models.CharField(max_length=50)
    budget = models.CharField(max_length=50)
    location = models.CharField(max_length=50)
    last_updated_timestamp = models.DateTimeField(auto_now=True)
    last_edited_by_userId = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='edited_projectcards')  # Correct related_name

    def __str__(self):
        return f"User {self.carduserId} - ProjectCard {self.projectCard}"
