from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.response import Response
from django.contrib.auth import login
from rest_framework.permissions import AllowAny
from axes.handlers.proxy import AxesProxyHandler
from axes.helpers import get_credentials, get_lockout_message
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer

from..serializer import LoginSerializer, LoginResponseSerializer

class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Login User",
        description="Login dengan username & password untuk mendapatkan session. Role diambil dari groups Django. Dibatasi 10x per menit per IP (ScopedRateThrottle) dan akun terkunci sementara selama 1 jam setelah 5x gagal (django-axes).",
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: inline_serializer(
                name="LoginError400",
                fields={
                    "non_field_errors": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "username": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                    "password": serializers.ListField(
                        child=serializers.CharField(), required=False
                    ),
                }
            ),
            429: inline_serializer(
                name="LoginError429",
                fields={"detail": serializers.CharField()}
            ),
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
                name="Error - Password Salah / User Tidak Ada",
                value={"non_field_errors": ["Username Atau Password Salah"]},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Field Hilang",
                value={"password": ["This field is required."]},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Akun Belum Verifkasi OTP",
                value={"detail": "Informasi Akun Tidak Di Temukan"},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Terlalu Banyak Percobaan / Akun Terkunci",
                value={"detail": "Request was throttled. Expected available in 60 seconds."},
                response_only=True,
                status_codes=["429"]
            ),
        ]
    )
    def post(self, request):
        credentials = get_credentials(
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if not AxesProxyHandler.is_allowed(request, credentials):
            return Response(
                {"detail": get_lockout_message()},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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