from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf_view(request):
    return JsonResponse({
        "message": "CSRF cookie berhasil dibuat"
    })