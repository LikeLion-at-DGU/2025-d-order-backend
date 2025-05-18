from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from booth.models import Booth, Table
from order.models import Cart, Order, Menu
from django.shortcuts import get_object_or_404
from .serializers import *
from django.db.models import Sum, F
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated


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

            if total_menu_num > menu.menu_remain:
                return Response({
                    "status": "fail",
                    "message": "주문 수량이 재고를 초과했습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            order.menu_num = total_menu_num
            order.save()

        except Order.DoesNotExist:
            if menu_num > menu.menu_remain:
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
        
        orders = Order.objects.filter(cart_id__in=carts).select_related('menu_id').order_by('-created_at')
        serializer = TableOrderSerializer(orders, many=True)

        return Response({
            "status": "success",
            "message": "주문 내역 조회 완료",
            "code": 200,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
class BoothOrderView(APIView):
    def get(self, request, booth_id):
        booth = get_object_or_404(Booth, id=booth_id)

        menus = Menu.objects.filter(booth_id=booth)

        order_complete_orders = Order.objects.filter(
            menu_id__in=menus,
            order_status='order_complete'
        )

        # 총 매출 계산 
        total_revenue_qs = Order.objects.filter(
            menu_id__in=menus,
            order_status__in=['order_complete', 'served_complete']
        ).annotate(
            item_total=F('menu_num') * F('menu_id__menu_price')
        ).aggregate(total=Sum('item_total'))

        total_revenue = total_revenue_qs['total'] or 0

        serializer = BoothOrderSerializer(order_complete_orders, many=True)
        return Response({
            "status": "success",
            "message": "주문 목록 및 매출 조회 완료",
            "code": 200,
            "data": {
                "total_revenue": total_revenue,
                "orders": serializer.data
            }
        }, status=status.HTTP_200_OK)
    
class OrderFixView(APIView):
    def patch(self, request, cart_id):
        cart = get_object_or_404(Cart, id=cart_id)

        cart_status = request.data.get('cart_status')
        
        if cart.cart_status:
            return Response({
                "status": "fail",
                "message": "이미 확정된 주문입니다.",
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)
        
        orders = Order.objects.filter(cart_id=cart).select_related('menu_id')

        for order in orders:
            menu = order.menu_id
            if order.menu_num > menu.menu_remain:
                return Response({
                    "status": "fail",
                    "message": f"재고가 부족합니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

        now_time = now()
        for order in orders:
            menu = order.menu_id
            menu.menu_remain -= order.menu_num
            menu.save()

            order.order_status = 'order_complete'
            order.created_at = now_time
            order.save()

        cart.cart_status = True
        cart.save()


        return Response({
            "status": "success",
            "message": "주문이 확정되었습니다.",
            "code": 200,
            "data": {
                "cart_id": cart.id,
                "cart_status": cart.cart_status
            }
        }, status=status.HTTP_200_OK)

class MenuCreateView(APIView):
    permission_classes = [IsAuthenticated]  #로그인한 사람만 등록 가능
    def post(self, request):
        serializer = MenuSerializer(data=request.data)
        if serializer.is_valid():
            menu = serializer.save()
            return Response({
                "status": "success",
                "message": "메뉴가 등록되었습니다.",
                "code": 201,
                "data": {
                    "booth_id": menu.booth_id.id,
                    "menu_id": menu.id,
                    "menu_name": menu.menu_name,
                    "menu_category": menu.menu_category,
                    "menu_price": menu.menu_price,
                    "menu_amount": menu.menu_amount,
                    "menu_remain": menu.menu_remain,
                    "menu_image": menu.menu_image.url if menu.menu_image else None
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": "fail",
            "message": "유효하지 않은 요청입니다.",
            "code": 400,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class UpdateOrderStatusView(APIView):
    def patch(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        new_status = request.data.get('order_status')

        order.order_status = 'served_complete'
        order.save()

        serializer = TableOrderSerializer(order)

        return Response({
            "status": "success",
            "message": "서빙 완료로 변경되었습니다.",
            "code": 200,
            "data": serializer.data
        }, status=status.HTTP_200_OK)