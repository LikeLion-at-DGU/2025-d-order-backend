from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError 
from .serializers import LoginSerializer,SignupSerializer,ManagerMyPageSerializer
from django.contrib.auth.models import User
from rest_framework.generics import RetrieveUpdateAPIView
from .serializers import ManagerMyPageSerializer
from manager.models import Manager
from booth.models import Table
from order.models import Menu
from rest_framework.permissions import IsAuthenticated, AllowAny
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from rest_framework_simplejwt.tokens import RefreshToken



class ManagerSignupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            manager = serializer.save()
            booth = manager.booth

            # 1) QR 코드 생성
            link = f"https://d-order.netlify.app/?id={booth.id}"
            img = qrcode.make(link)

            # 2) 메모리 버퍼에 저장
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            # 3) Booth.qr_code_image 에 붙이고 저장
            filename = f"booth_{booth.id}_qr.png"
            booth.qr_code_image.save(
                filename,
                ContentFile(buffer.getvalue()),
                save=True
            )
            buffer.close()

            #  회원가입 이후 table_num만큼 테이블 자동 생성
            for i in range(1, manager.table_num + 1):
                Table.objects.create(
                    booth_id=manager.booth,
                    table_num=i,
                    table_status='out'
                )
            # 2. 자릿세 메뉴 자동 생성
            if manager.seat_type in ['PT', 'PP']:
                # 중복 생성 방지
                if not Menu.objects.filter(
                    booth_id=manager.booth,
                    menu_name="테이블 이용료",
                    menu_category="테이블 이용료"
                ).exists():
                    # seat_type에 따라 가격, 설명 결정
                    if manager.seat_type == 'PT':
                        menu_price = manager.seat_tax_table
                        menu_description = "테이블"
                    elif manager.seat_type == 'PP':
                        menu_price = manager.seat_tax_person
                        menu_description = "인원수"
                    elif manager.seat_type == 'NO':
                        menu_price = 0
                        menu_description = " "

                    Menu.objects.create(
                        booth_id=manager.booth,
                        menu_name="테이블 이용료",
                        menu_category="테이블 이용료",
                        menu_price=menu_price,
                        menu_amount=999,
                        menu_remain=999,
                        menu_description=menu_description
                    )


            return Response({
                "status": "success",
                "message": "회원가입이 완료되었습니다.",
                "code": 201,
                "data": {
                    "manager_id": manager.user.id,
                    "booth_id": manager.booth.id,
                    "table_num": manager.table_num
                }
            }, status=201)

        return Response(serializer.errors, status=400)


class UsernameCheckView(APIView):
    def get(self, request):
        username = request.query_params.get("username")

        if username is None:
            return Response({
                "code": 400,
                "message": "username 파라미터가 필요합니다.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        is_available = not User.objects.filter(username=username).exists()

        return Response({
            "code": 200,
            "message": "아이디 중복체크에 성공했습니다.",
            "data": {
                "is_available": is_available
            }
        }, status=status.HTTP_200_OK)

class ManagerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        manager = serializer.validated_data['manager']

        # JWT 토큰 발급
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # ✅ 응답 본문에는 access만 포함
        response = Response({
            "message": "로그인 성공",
            "code": 200,
            "data": {
                "manager_id": manager.pk,
                "booth_id": manager.booth_id,
                "access_token": access_token  # JSON에 access만 포함
            }
        }, status=status.HTTP_200_OK)

        # refresh_token은 HttpOnly 쿠키로만 전송
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=True,      # 개발 중엔 False, 운영은 True
            samesite='Lax',
            max_age=7 * 24 * 60 * 60,
        )

        return response


class ManagerLogoutView(APIView):
    def post(self, request):
        response = Response({"message": "로그아웃 되었습니다."})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response





class ManagerMyPageView(RetrieveUpdateAPIView):
    serializer_class = ManagerMyPageSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Manager.objects.get(user=self.request.user)

    def get(self,request):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "message": "관리자 정보를 불러왔습니다.",
            "code": 201,
            "data": serializer.data
        }, status=201)

    def patch(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "관리자 정보가 수정되었습니다.",
            "code": 200,
            "data": serializer.data
        }, status=200)