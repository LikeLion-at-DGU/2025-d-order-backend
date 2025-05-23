from rest_framework.views import APIView
from rest_framework import mixins, generics
from rest_framework.response import Response
from rest_framework import status
from manager.models import Manager
from booth.models import Booth, Table
from order.models import Cart, Order, Menu
from django.shortcuts import get_object_or_404
from .serializers import *
from django.db.models import Sum, F
from django.utils.timezone import now
from rest_framework.permissions import IsAuthenticated, AllowAny


class ConfirmCartOrderView(APIView):
    def post(self, request):
        # 헤더에서 booth_id와 table_num 추출
        booth_id = request.headers.get("X-Booth-Id")
        table_num = request.headers.get("X-Table-Number")

        if not booth_id or not table_num:
            return Response({
                "status": "fail",
                "message": "헤더에 booth_id 또는 table_num이 없습니다.",
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            table = Table.objects.get(booth_id=booth_id, table_num=table_num)
        except Table.DoesNotExist:
            return Response({
                "status": "fail",
                "message": "해당 테이블이 존재하지 않습니다.",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ConfirmCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": "fail",
                "message": serializer.errors,
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        items = serializer.validated_data['items']

        booth = get_object_or_404(Booth, id=booth_id)
        table, _ = Table.objects.get_or_create(
            booth_id=booth,
            table_num=table_num,
            defaults={'table_status': 'active'}
        )

        has_previous_order = Cart.objects.filter(table_id=table, cart_status=True).exists()
        has_seat_tax = any(
            get_object_or_404(Menu, id=item['menu_id']).menu_category == "테이블 이용료"
            for item in items
        )

        if not has_previous_order and not has_seat_tax:
            return Response({
                "status": "fail",
                "message": "첫 주문에는 테이블 이용료를 반드시 포함해야 합니다.",
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        cart = Cart.objects.create(
            table_id=table,
            cart_status=False,
            total_price=0
        )

        now_time = now()
        total_price = 0
        created_orders = []

        for item in items:
            menu = get_object_or_404(Menu, id=item['menu_id'])
            menu_num = item['menu_num']

            if menu.menu_remain < menu_num:
                return Response({
                    "status": "fail",
                    "message": f"{menu.menu_name}은 {menu.menu_remain}개만큼만 주문할 수 있습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                cart_id=cart,
                menu_id=menu,
                menu_num=menu_num,
                menu_price=menu.menu_price,
                order_status="장바구니",
                created_at=now_time
            )
            menu.menu_remain -= menu_num
            menu.save()
            total_price += menu.menu_price * menu_num
            created_orders.append(order.id)

        cart.total_price = total_price
        cart.save()

        return Response({
            "status": "success",
            "message": "주문이 완료되었습니다.",
            "code": 201,
            "data": {
                "cart_id": cart.id,
                "table_id": table.id,
                "order_ids": created_orders,
                "total_price": total_price
            }
        }, status=status.HTTP_201_CREATED)
    
class TableOrderView(APIView):
    def get(self, request):
        booth_id = request.headers.get("X-Booth-Id")
        table_number = request.headers.get("X-Table-Number")

        if not booth_id or not table_number:
            return Response({
                "status": "fail",
                "message": "헤더에 booth_id 또는 table_number가 누락되었습니다.",
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            table = Table.objects.get(booth_id=booth_id, table_num=table_number)
        except Table.DoesNotExist:
            return Response({
                "status": "fail",
                "message": "해당 테이블이 존재하지 않습니다.",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)

        carts = Cart.objects.filter(table_id=table, cart_status=True)
        if not carts.exists():
            return Response({
                "stats": "fail",
                "message": "완료된 주문이 없습니다",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)
        
        orders = Order.objects.filter(cart_id__in=carts).select_related('menu_id').order_by('-created_at')
        serializer = TableOrderSerializer(orders, many=True)

        total_price = sum(
            order.menu_id.menu_price * order.menu_num for order in orders
        )

        return Response({
            "status": "success",
            "message": "주문 내역 조회 완료",
            "code": 200,
            "total_price": total_price,            
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

class MenuCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = MenuSerializer(data=request.data)

            # 1. 로그인한 유저의 Manager 조회 (예외 대비)
            try:
                manager = Manager.objects.get(user=request.user)
            except Manager.DoesNotExist:
                return Response({
                    "status": "fail",
                    "message": "유저에 해당하는 매니저 정보가 없습니다.",
                    "code": 403
                }, status=status.HTTP_403_FORBIDDEN)

            # 2. 시리얼라이저 유효성 검사
            if serializer.is_valid():
                try:
                    menu = serializer.save(booth_id=manager.booth)
                except Exception as e:
                    print("🔥 Menu 저장 중 오류:", str(e))
                    return Response({
                        "status": "fail",
                        "message": f"메뉴 저장 중 오류 발생: {str(e)}",
                        "code": 500
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                        "menu_image": request.build_absolute_uri(menu.menu_image.url) if menu.menu_image else None
                    }
                }, status=status.HTTP_201_CREATED)

            # 3. serializer.is_valid() 실패 시
            return Response({
                "status": "fail",
                "message": "유효하지 않은 요청입니다.",
                "code": 400,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("🔥 MenuCreateView 전역 오류:", str(e))
            return Response({
                "status": "fail",
                "message": f"서버 내부 오류 발생: {str(e)}",
                "code": 500
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
#메뉴 수정,삭제
class MenuPatchDeleteView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView
):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'menu_id'  # URL에서 <menu_id> 가져오기

    def get_queryset(self):
        manager = Manager.objects.get(user=self.request.user)
        return Menu.objects.filter(booth_id=manager.booth)
    
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
class MenuManagerListView(APIView):
    def get(self, request):
        manager = Manager.objects.get(user=request.user)

        # 로그인한 매니저의 부스 메뉴만 가져오기
        menus = Menu.objects.filter(booth_id=manager.booth)

        # 정렬 우선순위 설정
        category_order = {
            "테이블 이용료": 0,
            "메뉴": 1,
            "음료": 2
        }

        # 정렬 수행
        sorted_menus = sorted(
            menus,
            key=lambda m: (
                category_order.get(m.menu_category, 99),
                -m.menu_price,
                m.id
            )
        )

        # 직렬화
        serializer = MenuSerializer(sorted_menus, many=True)

        return Response({
            "status": "success",
            "message": "메뉴 리스트 조회 성공",
            "code": 200,
            "data": serializer.data
        }, status=200)

class UpdateOrderQuantityView(APIView):
    def patch(self, request, order_id):
        try:
            # 1. Order 객체 가져오기
            order = get_object_or_404(Order, id=order_id)
            menu = order.menu_id
            cart = order.cart_id

            # 2. 요청 데이터
            menu_num = request.data.get("menu_num")

            if menu_num is None:
                return Response({
                    "status": "fail",
                    "message": "menu_num이 누락되었습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            # 3. menu_num 유효성 검사
            try:
                menu_num = int(menu_num)
            except ValueError:
                return Response({
                    "status": "fail",
                    "message": "menu_num은 숫자여야 합니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            if menu_num < 1:
                return Response({
                    "status": "fail",
                    "message": "수량은 1개 이상이어야 합니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            # 4. 테이블 이용료 확인
            if menu.menu_name == "테이블 이용료" or menu.menu_category == "테이블 이용료" or menu.menu_category.lower() == "seat":
                return Response({
                    "status": "fail",
                    "message": "테이블 이용료 항목은 변경할 수 없습니다.",
                    "code": 403
                }, status=status.HTTP_403_FORBIDDEN)

            # 5. 재고 초과 여부 확인
            if menu_num > menu.menu_remain:
                return Response({
                    "status": "fail",
                    "message": f"재고({menu.menu_remain})보다 많은 수량은 담을 수 없습니다.",
                    "code": 400
                }, status=status.HTTP_400_BAD_REQUEST)

            # 6. 수량 변경
            order.menu_num = menu_num
            order.save()

            # 7. 카트 총 가격 재계산
            orders = Order.objects.filter(cart_id=cart)
            total_price = sum(o.menu_id.menu_price * o.menu_num for o in orders)
            cart.total_price = total_price
            cart.save()

            return Response({
                "status": "success",
                "message": "수량이 성공적으로 변경되었습니다.",
                "code": 200,
                "data": {
                    "order_id": order.id,
                    "menu_num": order.menu_num
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "fail",
                "message": str(e),
                "code": 500
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        menu = order.menu_id
        cart = order.cart_id

        # 테이블 이용료 항목 삭제 방지
        if menu.menu_name == "테이블 이용료" or menu.menu_category == "테이블 이용료" or menu.menu_category.lower() == "seat":
            return Response({
                "status": "fail",
                "message": "테이블 이용료 항목은 삭제할 수 없습니다.",
                "code": 403
            }, status=status.HTTP_403_FORBIDDEN)

        # 삭제 수행
        order.delete()

        # cart 총합 재계산
        remaining_orders = Order.objects.filter(cart_id=cart)
        total_price = sum(o.menu_id.menu_price * o.menu_num for o in remaining_orders)
        cart.total_price = total_price
        cart.save()

        return Response({
            "status": "success",
            "message": "해당 항목이 삭제되었습니다.",
            "code": 204
        }, status=status.HTTP_204_NO_CONTENT)

class MenuListView(APIView):
    def get(self, request):
        table_id = request.GET.get("table_id")
        if not table_id:
            return Response({
                "status": "error",
                "message": "table_id는 필수입니다.",
                "code": 400,
                "data": None
            }, status=400)

        table = get_object_or_404(Table, id=table_id)
        booth = table.booth_id
        menus = Menu.objects.filter(booth_id=booth)
        manager = get_object_or_404(Manager, booth=booth)

        # seat_type에 따라 요금 정보 정리
        seat_info = {"seat_type": "none", "seat_tax_person": 0}

        if manager.seat_type == "PP":  # 인당 요금
            seat_info = {
                "seat_type": "person",
                "seat_tax_person": manager.seat_tax_person or 0
            }
        elif manager.seat_type == "PT":  # 테이블당 요금
            seat_info = {
                "seat_type": "table",
                "seat_tax_table": manager.seat_tax_table or 0
            }
        elif manager.seat_type == "NO":
            seat_info = {
                "seat_type": "none"
            }

        # 메뉴 리스트 구성
        menu_list = []
        for menu in menus:
            menu_list.append({
                "menu_id": menu.id,
                "menu_name": menu.menu_name,
                "menu_description": menu.menu_description,
                "menu_price": menu.menu_price,
                "menu_image": request.build_absolute_uri(menu.menu_image.url) if menu.menu_image else None,
                "menu_type": "normal"  # 현재 menu_type은 없으므로 default
            })

        return Response({
            "status": "success",
            "message": "메뉴 목록 조회 성공",
            "code": 200,
            "data": {
                "seat": seat_info,
                "menus": menu_list
            }
        }, status=200)
        
class TotalRevenueView(APIView):
    def get(self, request):
        try:
            manager = Manager.objects.get(user=request.user)
        except Manager.DoesNotExist:
            return Response({
                "status": "error",
                "message": "부스 정보가 존재하지 않습니다.",
                "code": 404,
                "data": None
            }, status=404)

        booth = manager.booth
        tables = Table.objects.filter(booth_id=booth)

        total_revenue = Order.objects.filter(
            cart_id__table_id__in=tables,
            order_status="order_complete"
        ).aggregate(
            total=Sum(F("menu_num") * F("menu_price"))
        )["total"] or 0

        return Response({
            "status": "success",
            "message": "부스 매출 정보 조회 성공",
            "code": 200,
            "data": {
                "booth_id": booth.id,
                "booth_name": booth.name,
                "total_revenues": total_revenue
            }
        }, status=200)

class FinalizeOrderView(APIView):
    def post(self, request):
        table_id = request.data.get("table_id")

        if table_id is None:
            return Response({
                "status": "fail",
                "message": "table_id가 필요합니다.",
                "code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(table_id=table_id, cart_status=False)
        except Cart.DoesNotExist:
            return Response({
                "status": "fail",
                "message": "진행 중인 장바구니가 없습니다.",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": "success",
            "message": "주문이 완료되었습니다.",
            "code": 201,
            "data": {
                "cart_id": cart.id,
                "table_id": cart.table_id.id,
                "total_price": cart.total_price
            }
        }, status=status.HTTP_201_CREATED)

class LastOrderView(APIView):
    def get(self, request, table_id):
        # cart_status=False인 것 중에서 가장 최근 cart 하나 조회
        cart = Cart.objects.filter(table_id=table_id, cart_status=False).order_by('-id').first()

        if not cart:
            return Response({
                "status": "fail",
                "message": "해당 테이블의 완료된 주문이 없습니다.",
                "code": 404
            }, status=status.HTTP_404_NOT_FOUND)

        # 해당 cart에 연결된 주문들
        orders = Order.objects.filter(cart_id=cart)
        orders_serialized = TableOrderSerializer(orders, many=True).data

        return Response({
            "cart_id": cart.id,
            "table_id": cart.table_id.id,
            "cart_status": cart.cart_status,
            "total_price": cart.total_price,
            "orders": orders_serialized
        }, status=status.HTTP_200_OK)

class OrderCheckView(APIView):
    def post(self, request):
        booth_id = request.headers.get("X-Booth-Id")
        table_num = request.headers.get("X-Table-Number")
        password = request.data.get("order_check_password")

        if not booth_id or not table_num:
            return Response({
                "status": "error",
                "message": "헤더에 booth_id 또는 table_num이 누락되었습니다.",
                "code": 400,
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response({
                "status": "error",
                "message": "비밀번호가 누락되었습니다.",
                "code": 400,
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            booth = Booth.objects.get(id=int(booth_id))
        except Booth.DoesNotExist:
            return Response({
                "status": "error",
                "message": "해당 부스가 존재하지 않습니다.",
                "code": 404,
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            table = Table.objects.get(booth_id=booth, table_num=table_num)
        except Table.DoesNotExist:
            return Response({
                "status": "error",
                "message": "해당 테이블이 존재하지 않습니다.",
                "code": 404,
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        manager = get_object_or_404(Manager, booth=booth)

        if manager.order_check_password != password:
            return Response({
                "status": "error",
                "message": "비밀번호가 올바르지 않습니다.",
                "code": 401,
                "data": None
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 진행 중인 cart 조회
        cart = Cart.objects.filter(table_id=table, cart_status=False).order_by('-id').first()
        if not cart:
            return Response({
                "status": "error",
                "message": "진행 중인 주문이 없습니다.",
                "code": 404,
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        # 결제 총액
        total_price = cart.total_price

        # 주문 상태 업데이트
        orders = Order.objects.filter(cart_id=cart).select_related('menu_id')
        now_time = now()

        for order in orders:
            menu = order.menu_id
            menu.save()

            order.menu_price = menu.menu_price
            order.order_status = 'order_complete'
            order.created_at = now_time
            order.save()

        cart.cart_status = True
        cart.save()

        return Response({
            "status": "success",
            "message": "결제가 확인되었습니다.",
            "code": 200,
            "data": {
                "table_id": table.id,
                "table_num": table.table_num,
                "total_price": total_price
            }
        }, status=status.HTTP_200_OK)
    
class TableOrderGroupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        manager = Manager.objects.get(user=request.user)
        booth = manager.booth

        tables = Table.objects.filter(booth_id=booth)
        response_data = []

        for table in tables:
            carts = Cart.objects.filter(table_id=table, cart_status=True).order_by('created_at')

            for cart in carts:
                orders = Order.objects.filter(cart_id=cart).select_related('menu_id')
                order_data = []

                for order in orders:
                    menu = order.menu_id
                    order_data.append({
                        "menu_name": menu.menu_name,
                        "menu_image": request.build_absolute_uri(menu.menu_image.url) if menu.menu_image else None,
                        "menu_num": order.menu_num,
                        "order_status": order.order_status
                    })

                response_data.append({
                    "table_num": table.table_num,
                    "created_at": cart.created_at,
                    "orders": order_data
                })

        return Response({
            "status": "success",
            "message": "테이블별 주문 조회 성공",
            "code": 200,
            "data": response_data
        }, status=200)

class PublicMenuListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, booth_id):
        booth = get_object_or_404(Booth, id=booth_id)
        manager = get_object_or_404(Manager, booth=booth)

        menus = Menu.objects.filter(booth_id=booth)

        # 좌석 요금 정보 추출 (테이블 이용료 메뉴 찾기)
        table_fee = menus.filter(menu_category="테이블 이용료").first()

        # 나머지 메뉴는 필터링
        normal_menus = menus.exclude(menu_category="테이블 이용료")

        # 정렬 우선순위 적용
        category_order = {"메뉴": 1, "음료": 2}
        sorted_normal = sorted(
            normal_menus,
            key=lambda m: (
                category_order.get(m.menu_category, 99),
                -m.menu_price,
                m.id
            )
        )

        # 시리얼라이징
        serializer = MenuSerializer(sorted_normal, many=True, context={"request": request})

        # seat_info 구성
        if manager.seat_type == "PP":
            seat_info = {
                "seat_type": "person",
                "seat_tax_person": manager.seat_tax_person or 0
            }
        elif manager.seat_type == "PT":
            seat_info = {
                "seat_type": "table",
                "seat_tax_table": manager.seat_tax_table or 0
            }
        else:
            seat_info = {
                "seat_type": "none"
            }

        return Response({
            "status": "success",
            "message": "메뉴 목록 조회 성공",
            "code": 200,
            "data": {
                "booth_name": booth.name,
                "seat": seat_info,
                "menus": [
                    {
                        "menu_id": m["id"],
                        "menu_name": m["menu_name"],
                        "menu_description": m["menu_description"],
                        "menu_price": m["menu_price"],
                        "menu_remain": m["menu_remain"],
                        "menu_image": m["menu_image"],
                        "menu_category": m["menu_category"]
                    } for m in serializer.data
                ]
            }
        }, status=200)


# class OrderFixView(APIView):
#     def patch(self, request, cart_id):
#         cart = get_object_or_404(Cart, id=cart_id)
#         table = cart.table_id

#         cart_status = request.data.get('cart_status')
        
#         if cart.cart_status:
#             return Response({
#                 "status": "fail",
#                 "message": "이미 확정된 주문입니다.",
#                 "code": 400
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         orders = Order.objects.filter(cart_id=cart).select_related('menu_id')

#         now_time = now()
        
#         for order in orders:
#             menu = order.menu_id
#             menu.menu_remain -= order.menu_num
#             menu.save()

#             order.menu_price = menu.menu_price  #주문 시점 가격 저장
#             order.order_status = 'order_complete'
#             order.created_at = now_time
#             order.save()

#         cart.cart_status = True
#         cart.save()


#         return Response({
#             "status": "success",
#             "message": "주문이 확정되었습니다.",
#             "code": 200,
#             "data": {
#                 "cart_id": cart.id,
#                 "cart_status": cart.cart_status
#             }
#         }, status=status.HTTP_200_OK)

# class TableCartView(APIView):
#     def get(self, request):
#         booth_id = request.headers.get("X-Booth-Id")
#         table_number = request.headers.get("X-Table-Number")

#         if not booth_id or not table_number:
#             return Response({
#                 "status": "fail",
#                 "message": "헤더에 booth_id 또는 table_number가 누락되었습니다.",
#                 "code": 400
#             }, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             table = Table.objects.get(booth_id=booth_id, table_num=table_number)
#         except Table.DoesNotExist:
#             return Response({
#                 "status": "fail",
#                 "message": "해당 테이블이 존재하지 않습니다.",
#                 "code": 404
#             }, status=status.HTTP_404_NOT_FOUND)

#         try:
#             cart = Cart.objects.get(table_id=table, cart_status=False)
#         except Cart.DoesNotExist:
#             return Response({
#                 "status": "fail",
#                 "message": "장바구니가 존재하지 않습니다.",
#                 "code": 404
#             }, status=status.HTTP_404_NOT_FOUND)

#         orders = Order.objects.filter(cart_id=cart).select_related('menu_id')
#         serializer = CartSummarySerializer(orders, many=True)

#         return Response({
#             "status": "success",
#             "message": "장바구니 조회 완료",
#             "code": 200,
#             "data": {
#                 "cart_id": cart.id,
#                 "table_id": table.id,
#                 "total_price": cart.total_price,
#                 "orders": serializer.data
#             }
#         }, status=status.HTTP_200_OK)