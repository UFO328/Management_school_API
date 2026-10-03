from django.urls import path 
from .views import RegisterAPIView ,LoginAPIView,LogoutAPIView,csrf_view

urlpatterns = [
  path("login/",LoginAPIView.as_view(),name="login"),
  path("logout/",LogoutAPIView.as_view(),name="logout"),
  path("register/",RegisterAPIView.as_view(),name="register"),
  path('csrf/',csrf_view,name='csrf')
]