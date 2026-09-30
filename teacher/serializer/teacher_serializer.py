from rest_framework import serializers as sz
from ..models import Teacher 

class TeacherSerializer(sz.ModelSerializer):
  class Meta:
    model = Teacher
    fields = "__all__"