from rest_framework import viewsets as vw 
from ..serializer import StudentProfileSerializer 
from ..models import StudentProfile
from core.permission import SchoolModelPermissions


class StudentProfileViewSet(vw.ModelViewSet):
  serializer_class = StudentProfileSerializer
  permission_classes = [SchoolModelPermissions]
  
  def get_queryset(self):
    return StudentProfile.objects.select_related("student").order_by("-id")
    