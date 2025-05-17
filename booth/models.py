from django.db import models

# Create your models here.

class Booth(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    total_revenues = models.IntegerField(default=0)