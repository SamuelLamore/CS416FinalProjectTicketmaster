from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class FavoriteEvent(models.Model):
    event_id = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    displayOnProfile = models.BooleanField(default=False)
    displayPriority = models.IntegerField(default=0)