from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('id', 'menu_name', 'menu_category', 'menu_price', 'menu_remain')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_id', 'cart_status', 'total_price', 'created_at')

    def table_display(self, obj):
        return f"Table {obj.table_id.table_num} ({obj.table_id.booth.name})"
    table_display.short_description = 'Table Info'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'menu_id', 'menu_num', 'menu_price', 'order_status', 'created_at')

    def menu_display(self, obj):
        return obj.menu_id.menu_name
    menu_display.short_description = 'Menu Name'