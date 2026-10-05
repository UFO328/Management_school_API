from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from..serializer import RegisterSerializer

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Register Akun Baru",
        description="Membuat akun baru dengan validasi username, email unik dan password minimal 8 karakter.",
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegisterSuccess201",
                fields={"message": serializers.CharField()}
            ),
            400: inline_serializer(
                name="RegisterError400",
                fields={
                    "username": serializers.ListField(child=serializers.CharField(), required=False),
                    "email": serializers.ListField(child=serializers.CharField(), required=False),
                    "password": serializers.ListField(child=serializers.CharField(), required=False),
                }
            )
        },
        tags=["Auth"],
        examples=[
            OpenApiExample(
                name="Request Valid",
                value={
                    "username": "johndoe",
                    "email": "john@mail.com",
                    "password": "password12345"
                },
                request_only=True
            ),
            OpenApiExample(
                name="Response Sukses",
                value={"message": "Akun Berhasil Di Buat"},
                response_only=True,
                status_codes=["201"]
            ),
            OpenApiExample(
                name="Error - Username sudah ada",
                value={"username": ["Username Tidak Tersedia"]},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Email sudah ada",
                value={"email": ["Email Tidak Tersedia"]},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Error - Password terlalu pendek",
                value={"password": ["This password is too short.", "This password is too common."]},
                response_only=True,
                status_codes=["400"]
            ),
        ]
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Akun Berhasil Di Buat"},
            status=status.HTTP_201_CREATED
        )