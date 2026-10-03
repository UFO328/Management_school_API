from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import logout
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout User",
        description="Menghapus session aktif user. Memerlukan session cookie + CSRF token yang valid.",
        request=None,
        responses={
            204: None,
            401: None,
        },
        tags=["Auth"],
    )
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)