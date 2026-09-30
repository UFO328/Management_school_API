from rest_framework import viewsets as vw 
from core.permission import SchoolModelPermissions
from rest_framework import serializers as sz
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema,OpenApiExample,inline_serializer
from ..serializer import StudentSerializer 
from ..models import Student

#view untuk melakukan CRUD
class StudentViewSet(vw.ModelViewSet):
  serializer_class = StudentSerializer
  permission_classes = [SchoolModelPermissions]
  
  def list(self, request, *args, **kwargs):
    
    print("REQUEST USER:", request.user)
    print("AUTHENTICATED:", request.user.is_authenticated)
    print("SESSION:", request.session.session_key)

    return super().list(request, *args, **kwargs)
  def get_queryset(self):
    return Student.objects.all().order_by("-fullname")
    