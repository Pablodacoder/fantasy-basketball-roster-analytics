from django.db import models

# Create your models here.
class Manager(models.Model):
  id = models.PositiveIntegerField(primary_key=True)
  name = models.CharField(default="Manager")
  