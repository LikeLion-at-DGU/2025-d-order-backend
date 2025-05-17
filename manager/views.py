from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.exceptions import ValidationError 
from .serializers import LoginSerializer,SignupSerializer
from django.contrib.auth.models import User


class ManagerSignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.save(), status=201)
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
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        try:
            # raise_exception=True면 validate()에서 던진 ValidationError가 바로 터집니다
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            # e.detail이 우리가 validate()에서 만든 dict 그대로 들어있음
            return Response(e.detail, status=status.HTTP_200_OK)

        # 검증 성공 시, validate()에서 리턴한 dict (message, code, data, token)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class ManagerLogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # 로그아웃 refresh 토큰  db에 저장
            return Response({"message": "로그아웃 되었습니다."}, status=200)
        except KeyError:
            return Response({"message": "Refresh token이 필요합니다."}, status=400)
        except TokenError:
            return Response({"message": "유효하지 않은 토큰입니다."}, status=400)