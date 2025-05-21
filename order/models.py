from django.db import models
from booth.models import Booth, Table
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

# Create your models here.
class Menu(models.Model):
    CATEGORY_CHOICES = ( #둘 중 하나로 저장 카테고리 
        ("음료", "음료"),
        ("메뉴", "메뉴"),
    )
    id = models.AutoField(primary_key=True)
    booth_id = models.ForeignKey(Booth, on_delete=models.CASCADE)
    menu_name = models.CharField(max_length=20)
    menu_description = models.CharField(max_length=30, blank=True, null=True)
    menu_category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    menu_price = models.IntegerField()
    menu_amount = models.IntegerField()
    menu_remain = models.IntegerField()
    menu_image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    # def __str__(self):
    #     return self.menu_name

    
    
    def compress_image(self, image_field_file, image_field_name):
        img = Image.open(image_field_file)

        # Pillow는 JPEG 저장을 위해 RGB로 변환 필요
        if img.mode != 'RGB':
            img = img.convert('RGB')

        output = BytesIO()
        img.save(output, format='JPEG', quality=70)  # 압축 품질 조절 (0~100)
        output.seek(0)

        compressed_image = ContentFile(output.read(), name=image_field_file.name)
        setattr(self, image_field_name, compressed_image)

    def save(self, *args, **kwargs):
        # 처음 생성 시에만 menu_remain을 menu_amount와 같게 설정
        if self._state.adding and self.menu_remain is None:
            self.menu_remain = self.menu_amount
        # 이미지 있을 때만 압축
        if self.menu_image:
            self.compress_image(self.menu_image, 'menu_image')
        super().save(*args, **kwargs)


class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    table_id = models.ForeignKey(Table, on_delete=models.CASCADE)
    cart_status = models.BooleanField(default=False)
    total_price = models.IntegerField()

    
class Order(models.Model):
    id = models.AutoField(primary_key=True)
    cart_id = models.ForeignKey(Cart, on_delete=models.CASCADE)
    menu_id = models.ForeignKey(Menu, on_delete=models.CASCADE)
    menu_num = models.IntegerField()
    menu_price = models.IntegerField(default=0)  # 주문 당시 가격(수정 구분)
    order_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

