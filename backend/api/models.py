# Create your models here.
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200,)
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField()
    