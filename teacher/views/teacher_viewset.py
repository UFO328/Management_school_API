from rest_framework import viewsets as vw 
from ..serializer import TeacherSerializer 
from ..models import Teacher 
from core.permission import SchoolModelPermissions

class TeacherViewSet(vw.ModelViewSet):
  serializer_class = TeacherSerializer
  permission_classes = [SchoolModelPermissions]
  
  def get_queryset(self):
    return Teacher.objects.all()