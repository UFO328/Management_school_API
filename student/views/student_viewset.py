from rest_framework import viewsets as vw 
from core.permission import SchoolModelPermissions
from rest_framework.exceptions import ValidationError 
from django.db.models import ProtectedError
from ..serializer import StudentSerializer 
from ..models import Student

#view untuk melakukan CRUD
class StudentViewSet(vw.ModelViewSet):
  serializer_class = StudentSerializer
  permission_classes = [SchoolModelPermissions]
  

  def get_queryset(self):
    return Student.objects.all().order_by("fullname")

  def perform_destroy(self,intances):
    try:
      intances.delete()
    except ProtectedError:
      raise ValidationError({"detail":"User Ini masih Memiliki Profile"})
      