from django.db import models
from django.contrib.auth.models import User
from booth.models import Booth

class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="manager_profile") #user를 manager pk로 사용
    booth = models.OneToOneField(Booth, on_delete=models.CASCADE, related_name='manager')
    table_num = models.IntegerField(default=0)
    order_check_password = models.CharField(max_length=10)
    account = models.CharField(max_length=30)
    depositor = models.CharField(max_length=20)
    bank = models.CharField(max_length=20)
    seat_tax_person = models.IntegerField(null=True, blank=True)
    seat_tax_table =models.IntegerField(null=True, blank=True)


    SEAT_TYPE_CHOICES = [
        ('NO', 'No Seat Tax'),
        ('PP', 'Seat Tax Per Person'),
        ('PT', 'Seat Tax Per Table'),
    ]

    seat_type = models.CharField(
        max_length=2,
        choices=SEAT_TYPE_CHOICES,
        default='NO'
    )

    def __str__(self):
        return f"{self.user.username} (@{self.booth.name})"
    