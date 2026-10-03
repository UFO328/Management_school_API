from rest_framework import viewsets as vw 
from ..serializer import TeacherSerializer 
from ..models import Teacher 
from core.permission import SchoolModelPermissions
from rest_framework.exceptions import ValidationError 
from django.db.models import ProtectedError

class TeacherViewSet(vw.ModelViewSet):
  serializer_class = TeacherSerializer
  permission_classes = [SchoolModelPermissions]
  
  def get_queryset(self):
    return Teacher.objects.all().order_by("id")

  def perform_destroy(self,intances):
    try:
      intances.delete()
    except ProtectedError:
      raise ValidationError({"detail":"User Ini masih Memiliki Profile"})
      