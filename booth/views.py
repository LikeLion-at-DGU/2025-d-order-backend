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
from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Booth
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

class CookieTokenRefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token is None:
            return Response({"message": "refresh_token 쿠키가 없습니다."}, status=401)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({"access": access_token}, status=200)
        except TokenError:
            return Response({"message": "리프레시 토큰이 유효하지 않습니다."}, status=401)


class BoothQRView(APIView):

    permission_classes = [IsAuthenticated] 

    def get(self, request):
        booth_id = request.query_params.get('booth_id')
        if not booth_id:
            return Response(
                {"message": "booth_id 쿼리 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        booth = get_object_or_404(Booth, id=booth_id)

        if not booth.qr_code_image:
            return Response(
                {"message": "QR 코드가 아직 생성되지 않았습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

       
        return FileResponse(
            booth.qr_code_image.open('rb'),
            content_type='image/png'
        )



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
                cart_id__cart_status=True,
                order_status__in=['order_complete', 'served_complete']
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
                "table_status": table.table_status,
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
        booth   = manager.booth
        table   = get_object_or_404(Table, booth_id=booth, table_num=table_num)

        orders_all = (
            Order.objects
                 .filter(
                     cart_id__table_id=table,
                     cart_id__cart_status=True,
                     order_status__in=['order_complete', 'served_complete']
                 )
                 .select_related('menu_id')
                 .order_by('-created_at')
        )

        first_order = orders_all.first()
        total_price = orders_all.aggregate(
            total=Sum(F('menu_num') * F('menu_id__menu_price'))
        )['total'] or 0

       # Serializer에 request를 context로 넘김
        orders_serialized = FullOrderSerializer(
            orders_all,
            many=True,
            context={'request': request}
        ).data

        return Response({
            "status":  "success",
            "message": "테이블 상세 조회 성공",
            "code":    200,
            "data": {
                "table_num":   table.table_num,
                "table_price": total_price,
                "table_status":table.table_status,
                "created_at":  first_order.created_at if first_order else None,
                "orders":      orders_serialized
            }
        })



class CancelOrUpdateOrderView(APIView):
    def patch(self, request, table_num, order_id):
        manager = get_object_or_404(Manager, user=request.user)
        booth = manager.booth

        table = get_object_or_404(Table, booth_id=booth.id, table_num=table_num)
        order = get_object_or_404(
            Order,
            id=order_id,
            cart_id__table_id=table,
            cart_id__cart_status=True 
        )
        
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
            "code": 200,
            "data": {
                "table_id": table.id,
                "table_num": table.table_num,
                "table_status": table.table_status
            }
        }, status=200)

class EnterTableView(APIView):
    def post(self, request):
        booth_id = request.data.get('booth_id')
        table_num = request.data.get('table_num')
        table_id = request.data.get('table_id')

        # 1. 유효한 테이블인지 확인
        try:
            booth = Booth.objects.get(id=booth_id)
            table = Table.objects.get(id=table_id, booth_id=booth, table_num=table_num)
        except Booth.DoesNotExist:
            return Response({
                "status": "error",
                "message": "올바르지 않은 부스 ID입니다.",
                "code": 404,
                "data": None
            }, status=404)
        except Table.DoesNotExist:
            return Response({
                "status": "error",
                "message": "올바르지 않은 테이블 번호입니다.",
                "code": 404,
                "data": None
            }, status=404)

        # 2. 이미 입장한 테이블이면 에러
        if table.table_status == "activate":
            return Response({
                "status": "error",
                "message": "이미 입장한 테이블 번호입니다. 다시 확인해주세요.",
                "code": 409,
                "data": None
            }, status=409)

        # 3. 테이블 상태를 활성화로 변경
        table.table_status = "activate"
        table.save()

        # 4. 새 cart 생성
        cart = Cart.objects.create(
            table_id=table,
            cart_status=True,
            total_price=0
        )

        return Response({
            "status": "success",
            "message": "입장 성공! 새 cart 생성됨",
            "code": 201,
            "data": {
                "table_id": table.id,
                "table_num": table.table_num,
                "booth_id": booth.id,
                "booth_name": booth.name,
                "table_status": table.table_status,
                "cart_status": str(cart.cart_status).lower(),  # true
                "cart_id": cart.id
            }
        }, status=201)
