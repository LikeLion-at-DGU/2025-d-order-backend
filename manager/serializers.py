# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from manager.models import Manager
from booth.models import Booth
from django.contrib.auth.models import User


class SignupSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    booth_name = serializers.CharField()

    table_num = serializers.IntegerField()
    order_check_password = serializers.CharField()  
    account = serializers.CharField()              
    depositor = serializers.CharField()
    bank = serializers.CharField()

    seat_type = serializers.CharField()
    seat_tax_person = serializers.IntegerField()
    seat_tax_table = serializers.IntegerField()

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"]
        )

        booth = Booth.objects.create(
            name=validated_data["booth_name"]
        )

        manager = Manager.objects.create(
            user=user,
            booth=booth,
            table_num=validated_data["table_num"],
            order_check_password=validated_data["order_check_password"],
            account=validated_data["account"],
            depositor=validated_data["depositor"],
            bank=validated_data["bank"],
            seat_type=validated_data["seat_type"],
            seat_tax_person=validated_data["seat_tax_person"],
            seat_tax_table=validated_data["seat_tax_table"]
        )

        return {
            "message": "회원가입에 성공하셨습니다",
            "code": 201,
            "data": {
                "manager_id": manager.pk,
                "booth_id": booth.pk,
                "booth_name": booth.name
            }
        }






class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")


        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError({
                "message": "아이디 또는 비밀번호가 올바르지 않습니다.",
                "code": 401,
                "data": None,
                "token": None
            })

        manager = Manager.objects.get(user=user)
        refresh = RefreshToken.for_user(user)

        return {
            "message": "로그인 성공",
            "code": 200,
            "data": {
                "manager_id": manager.pk,
                "booth_id": manager.booth_id
            },
            "token": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }
        }
