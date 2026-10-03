from rest_framework import serializers as sz 
from student.models import Student 


class StudentOutputSerializer(sz.ModelSerializer):
  class Meta:
    model = Student
    fields = ["id","fullname","nis","nik","nisn","gender","status","is_active"]