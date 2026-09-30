from rest_framework import serializers as sz 
from ..models import Student 

class StudentSerializer(sz.ModelSerializer):
  class Meta:
    model = Student 
    fields = "__all__"