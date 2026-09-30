from django.urls import path 
from .views import RegisterAPIView ,LoginAPIView,csrf_view

urlpatterns = [
  path("login/",LoginAPIView.as_view(),name="login"),
  path("register/",RegisterAPIView.as_view(),name="register"),
  path('csrf/',csrf_view,name='csrf')
]