from rest_framework import serializers as sz 
from ..models import Student 

class StudentSerializer(sz.ModelSerializer):
  is_active = sz.BooleanField(default=True)
  
  class Meta:
    model = Student 
    fields = "__all__"