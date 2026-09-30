from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.response import Response
from django.contrib.auth import login
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer

from..serializer import LoginSerializer, LoginResponseSerializer

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Login User",
        description="Login dengan username & password untuk mendapatkan session. Role diambil dari groups Django.",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: inline_serializer(
                name="LoginError400",
                fields={"detail": serializers.CharField()}
            )
        },
        tags=["Auth"],
        examples=[
            OpenApiExample(
                name="Contoh Request Login",
                value={"username": "admin", "password": "admin123"},
                request_only=True
            ),
            OpenApiExample(
                name="Contoh Response Sukses",
                value={
                    "message": "Berhasil Login",
                    "user_role": ["admin", "staff"],
                    "user_id": 1,
                    "username": "admin"
                },
                response_only=True,
                status_codes=["200"]
            ),
            OpenApiExample(
                name="Error - Password Salah",
                value={"detail": "Username atau password salah"},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Akun Belum Verifkasi OTP",
                value={"detail": "Informasi Akun Tidak Di Temukan"},
                response_only=True,
                status_codes=["400"]
            ),
        ]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user_role = list(user.groups.values_list("name", flat=True))
        login(request, user)
        return Response({
            "message": "Berhasil Login",
            "user_role": user_role,
            "user_id": user.id,
            "username": user.username
        }, status=status.HTTP_200_OK)