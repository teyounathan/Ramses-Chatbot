from django.db import models
from django.utils import timezone

class Message(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    date = models.DateTimeField(default=timezone.now)