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
    menu_name = serializers.CharField(source='menu_id.menu_name')
    menu_price = serializers.IntegerField(source='menu_id.menu_price')

    class Meta:
        model = Order
        fields = ('id', 'menu_name', 'menu_price', 'menu_num', 'order_status')

