from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from manager.models import Manager
from booth.models import Booth, Table
from order.models import Cart, Order, Menu
from django.shortcuts import get_object_or_404
from .serializers import *
from django.db.models import Sum, F
from django.utils.timezone import now

class TableListView(APIView):

    def get(self, request):
        manager = Manager.objects.get(user=request.user)
        booth = manager.booth

        # 부스에 속한 모든 테이블 가져오기
        tables = Table.objects.filter(booth_id=booth).order_by('table_num')
        response_data = []

        for table in tables:
            # 해당 테이블의 'order_complete' 주문만 필터링
            orders_all = Order.objects.filter(
                cart_id__table_id=table,
                order_status='order_complete'
            ).select_related('menu_id').order_by('created_at')

            first_order = orders_all.first()
            recent_orders = orders_all.order_by('-created_at')[:3]

            total_price = orders_all.aggregate(
                total=Sum(F('menu_num') * F('menu_id__menu_price'))
            )['total'] or 0

            orders_serialized = SimpleOrderSerializer(recent_orders, many=True).data

            response_data.append({
                "table_num": table.table_num,
                "table_price": total_price,
                "created_at": first_order.created_at if first_order else None,
                "orders": orders_serialized
            })

        return Response({
            "status": "success",
            "message": "테이블 목록 조회 성공",
            "code": 200,
            "data": response_data
        }, status=200)

class TableDetailView(APIView):
    def get(self, request, table_num):
        manager = get_object_or_404(Manager, user=request.user)
        booth = manager.booth
        table = get_object_or_404(Table, booth_id=booth, table_num=table_num)

        orders_all = Order.objects.filter(
            cart_id__table_id=table,
            cart_id__cart_status=True,
            order_status='order_complete'
        ).select_related('menu_id').order_by('-created_at')

        first_order = orders_all.first()
        total_price = orders_all.aggregate(
            total=Sum(F('menu_num') * F('menu_id__menu_price'))
        )['total'] or 0

        orders_serialized = FullOrderSerializer(orders_all, many=True).data

        return Response({
            "status": "success",
            "message": "테이블 상세 조회 성공",
            "code": 200,
            "data": {
                "table_num": table.table_num,
                "table_price": total_price,
                "created_at": first_order.created_at if first_order else None,
                "orders": orders_serialized
            }
        })
class CancelOrUpdateOrderView(APIView):
    def patch(self, request, table_num, order_id):
        manager = get_object_or_404(Manager, user=request.user)
        booth = manager.booth

        table = get_object_or_404(Table, booth_id=booth.id, table_num=table_num)
        order = get_object_or_404(Order, id=order_id, cart_id__table_id=table)
        
        action = request.data.get("action")
        
        if action == "increase":
            order.menu_num += 1
            order.save()
            return Response({
                "status": "success",
                "message": "주문 수량 1 증가",
                "code": 200,
                "data": {
                    "order_id": order.id,
                    "menu_name": order.menu_id.menu_name,
                    "menu_num": order.menu_num
                }
            }, status=200)

        elif action == "decrease":
            if order.menu_num > 1:
                order.menu_num -= 1
                order.save()
                return Response({
                    "status": "success",
                    "message": "주문 수량 1 감소",
                    "code": 200,
                    "data": {
                        "order_id": order.id,
                        "menu_name": order.menu_id.menu_name,
                        "menu_num": order.menu_num
                    }
                }, status=200)
            else:
                order.delete()
                return Response({
                    "status": "success",
                    "message": "수량 0이 되어 주문이 삭제되었습니다.",
                    "code": 200,
                    "data": {
                        "order_id": order_id,
                        "menu_name": order.menu_id.menu_name
                    }
                }, status=200)

        return Response({
            "status": "fail",
            "message": "올바른 action 값이 필요합니다. ('increase' 또는 'decrease')",
            "code": 400
        }, status=400)
    
class ResetTableView(APIView):
    def post(self, request, table_num):
        # 1. 로그인한 관리자
        manager = get_object_or_404(Manager, user=request.user)
        booth = manager.booth

        # 2. 해당 부스의 table_num 테이블 가져오기
        table = get_object_or_404(Table, booth_id=booth.id, table_num=table_num)

        # 3. 현재 활성 cart 비활성화
        Cart.objects.filter(table_id=table, cart_status=True).update(cart_status=False)

        # 4. 테이블 상태를 'out'으로 변경
        table.table_status = "out"
        table.save()

        return Response({
            "status": "success",
            "message": f"{table.table_num}번 테이블이 리셋되었습니다.",
            "code": 200
        }, status=200)
