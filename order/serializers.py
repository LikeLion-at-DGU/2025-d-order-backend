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
    
class CartSummarySerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu_id.menu_name', read_only=True)
    menu_price = serializers.IntegerField(source='menu_id.menu_price', read_only=True)

    class Meta:
        model=Order
        fields = ['id', 'menu_id', 'menu_name', 'menu_price', 'menu_num']

class TableOrderSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu_id.menu_name', read_only=True)
    menu_price = serializers.IntegerField(source='menu_id.menu_price', read_only=True)

    class Meta:
        model=Order
        fields = ['id',        
            'cart_id',
            'menu_id',
            'menu_name',
            'menu_price',
            'menu_num',
            'order_status',
            'created_at'
        ]

class BoothOrderSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu_id.menu_name', read_only=True)
    menu_price = serializers.IntegerField(source='menu_id.menu_price', read_only=True)
    table_num = serializers.IntegerField(source='cart_id.table_id.table_num', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'menu_name',
            'menu_price',
            'menu_num',
            'order_status',
            'created_at',
            'table_num'
        ]

class MenuSerializer(serializers.ModelSerializer):
    booth_id = serializers.PrimaryKeyRelatedField(read_only=True)
    menu_image = serializers.ImageField(use_url=True, required=False)
    
    class Meta:
        model = Menu
        fields = '__all__'
        extra_kwargs = {
            'menu_remain': {'required': False}  
        }

    def validate_menu_category(self, value):
        if value not in ['음료', '메뉴', '테이블 이용료']:
            raise serializers.ValidationError("menu_category는 '음료', '메뉴', '테이블 이용료' 중 하나여야 합니다.")
        return value
    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # 조건: 카테고리가 "테이블 이용료"일 때 특정 필드 제거
        if instance.menu_category == "테이블 이용료":
            rep.pop("menu_amount", None)
            rep.pop("menu_remain", None)

        return rep

class OrderItemSerializer(serializers.Serializer):
    menu_id = serializers.IntegerField()
    menu_num = serializers.IntegerField(min_value=1)

class ConfirmCartSerializer(serializers.Serializer):
    booth_id = serializers.IntegerField()
    table_num = serializers.CharField()
    items = OrderItemSerializer(many=True)