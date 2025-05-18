from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from booth.models import Booth, Table
from order.models import Cart, Order, Menu
from django.shortcuts import get_object_or_404
from .serializers import *


class AddToCartView(APIView):
    def post(self, request):

        serializer = AddToCartRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": "fail",
                "message": serializer.errors,
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        booth_id = request.data.get('booth_id')
        table_num = request.data.get('table_num')
        menu_id = request.data.get('menu_id')
        menu_num = int(request.data.get('menu_num', 1))

        # 1. booth 존재 확인
        booth = get_object_or_404(Booth, id=booth_id)

        # 2. table 조회 or 생성
        table, _ = Table.objects.get_or_create(
            booth_id=booth,
            table_num=table_num,
            defaults={'table_status': 'active'}
        )

        # 3. cart_status=False인 Cart 조회 or 생성
        cart, _ = Cart.objects.get_or_create(
            table_id=table,
            cart_status=False,
            defaults={'total_price': 0}
        )

        # 4. menu 확인
        menu = get_object_or_404(Menu, id=menu_id)

        # 5. 동일한 메뉴가 이미 주문되었는지 확인
        try:
            order = Order.objects.get(cart_id=cart, menu_id=menu)
            total_menu_num = order.menu_num + menu_num

            if total_menu_num > menu.menu_amount:
                return Response({
                    "status": "fail",
                    "message": "주문 수량이 재고를 초과했습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            order.menu_num = total_menu_num
            order.save()

        except Order.DoesNotExist:
            if menu_num > menu.menu_amount:
                return Response({
                    "status": "fail",
                    "message": "주문 수량이 재고를 초과했습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                cart_id=cart,
                menu_id=menu,
                menu_num=menu_num,
                order_status='장바구니',
            )

        # 6. cart 가격 갱신
        cart.total_price += menu.menu_price * menu_num
        cart.save()

        # 7. 응답
        return Response({
            "status": "success",
            "message": "장바구니에 메뉴가 담겼습니다.",
            "code": 201,
            "data": {
                "cart_id": cart.id,
                "table_id": table.id,
                "menu_id": menu.id,
                "menu_num": order.menu_num
            }
        }, status=status.HTTP_201_CREATED)

class TableCartView(APIView):
    def get(self, request, table_id):
        table = get_object_or_404(Table, id=table_id)

        try:
            cart = Cart.objects.get(table_id=table, cart_status=False)
        except Cart.DoesNotExist:
            return Response({
                "status": "fail",
                "message": "장바구니가 존재하지 않습니다.",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(cart_id=cart).select_related('menu_id')
        serializer = CartSummarySerializer(orders, many=True)

        return Response({
            "status": "success",
            "message": "장바구니 조회 완료",
            "code": 200,
            "data": {
                "cart_id": cart.id,
                "table_id": table.id,
                "total_price": cart.total_price,
                "orders": serializer.data
            }
        }, status=status.HTTP_200_OK)
    
class TableOrderView(APIView):
    def get(self, request, table_id):
        table = get_object_or_404(Table, id=table_id)

        carts = Cart.objects.filter(table_id=table, cart_status=True)

        if not carts.exists():
            return Response({
                "stats": "fail",
                "message": "완료된 주문이 없습니다",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)
        
        orders = Order.objects.filter(cart_id__in=carts).select_related('menu_id')
        serializer = TableOrderSerializer(orders, many=True)

        return Response({
            "status": "success",
            "message": "주문 내역 조회 완료",
            "code": 200,
            "data": serializer.data
        }, status=status.HTTP_200_OK)