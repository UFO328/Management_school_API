from rest_framework import viewsets as vw 
from ..serializer import TeacherProfileSerializer 
from ..models import Teacher,TeacherProfile
from core.permission import SchoolModelPermissions

class TeacherProfileViewSet(vw.ModelViewSet):
  serializer_class = TeacherProfileSerializer
  permission_classes = [SchoolModelPermissions]
  
  def get_queryset(self):
    return TeacherProfile.objects.select_related("teacher")