from django.db import models

# Create your models here.

class Booth(models.Model):
    id = models.AutoField(primary_key=True) # 자동 생성 되므로 생략
    name = models.CharField(max_length=30)
    total_revenues = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
class Table(models.Model):
    id = models.AutoField(primary_key=True)
    booth_id = models.ForeignKey('Booth', on_delete=models.CASCADE)
    table_num = models.IntegerField()
    table_status = models.CharField(max_length=10)