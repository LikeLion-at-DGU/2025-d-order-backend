from django.contrib import admin
from .models import *


admin.site.register(Booth)

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_num', 'booth_name')

    def booth_name(self, obj):
        return obj.booth_id.name
    booth_name.short_description = 'Booth Name'

