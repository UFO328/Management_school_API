from rest_framework import serializers as sz 
from teacher.models import Teacher 

class TeacherOutputSerializer(sz.ModelSerializer):
  class Meta:
    model = Teacher 
    fields = ['id','fullname']