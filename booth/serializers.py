from rest_framework import serializers
from .models import *
from order.models import Order
from rest_framework import serializers
class SimpleOrderSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu_id.menu_name')
    menu_price = serializers.IntegerField(source='menu_id.menu_price')

    class Meta:
        model = Order
        fields = ['menu_name', 'menu_price', 'menu_num']


class TableSummarySerializer(serializers.Serializer):
    table_num = serializers.IntegerField()
    table_price = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    orders = SimpleOrderSerializer(many=True)

class FullOrderSerializer(serializers.ModelSerializer):
    menu_name  = serializers.CharField(source='menu_id.menu_name')
    menu_price = serializers.IntegerField(source='menu_id.menu_price')
    menu_image = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = (
            'id',
            'menu_name',
            'menu_price',
            'menu_num',
            'menu_image',
            'order_status',
        )

    def get_menu_image(self, obj):
        img = obj.menu_id.menu_image
        if not img:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(img.url) if request else img.url