from django.contrib import admin
from .models import *
from order.models import Order
from django.db.models import Sum, F



@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_num', 'booth_name')

    def booth_name(self, obj):
        return obj.booth_id.name
    booth_name.short_description = 'Booth Name'

class BoothAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'total_revenue_display', 'qr_code_image') 

    def total_revenue_display(self, obj):
        total = Order.objects.filter(
            menu_id__booth_id=obj.id,
            order_status__in=['order_complete', 'served_complete']
        ).aggregate(
            total=Sum(F('menu_num') * F('menu_id__menu_price'))
        )['total'] or 0

        return f"{total:,}원" 

    total_revenue_display.short_description = '총 매출'

admin.site.register(Booth, BoothAdmin)
