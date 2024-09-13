from django.db import models
from passlib.hash import pbkdf2_sha256
class User(models.Model):
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)
    userId = models.AutoField(primary_key=True)
    role = models.CharField(max_length=50, default='CEO')  # Add a default role, such as 'user'
    username = models.CharField(max_length=255, unique=True)
    
    def verifyPassword(self, raw_password):
        return pbkdf2_sha256.verify(raw_password, self.password)
    
    def __str__(self):
        return self.email + " " +  self.username
