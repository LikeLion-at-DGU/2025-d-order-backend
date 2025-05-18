from rest_framework import serializers
from .models import *

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'cart_id', 'menu_id', 'menu_num', 'order_status', 'created_at', 'updated_at']

class CartSerializer(serializers.ModelSerializer):
    orders = OrderSerializer(many=True, read_only=True, source='order_set')  # Cart에 연결된 모든 Order

    class Meta:
        model = Cart
        fields = ['id', 'table_id', 'cart_status', 'total_price', 'orders']

class AddToCartRequestSerializer(serializers.Serializer):
    booth_id = serializers.IntegerField()
    table_num = serializers.IntegerField()
    menu_id = serializers.IntegerField()
    menu_num = serializers.IntegerField(min_value=1)

    def validate_menu_num(self, value):
        if value < 1:
            raise serializers.ValidationError("menu_num은 1 이상이어야 합니다.")
        return value
    

class OrderSummarySerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu_id.menu_name', read_only=True)
    menu_price = serializers.IntegerField(source='menu_id.menu_price', read_only=True)

    class Meta:
        model=Order
        fields = ['id', 'menu_id', 'menu_name', 'menu_price', 'menu_num']