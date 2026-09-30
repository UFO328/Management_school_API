from django.db import models as md 
from .student_model import Student 

class StudentProfile(md.Model):
  student = md.OneToOneField(Student,on_delete=md.PROTECT,related_name="profile_student")
  email = md.EmailField()
  phone = md.CharField(max_length=14)
  birth_date = md.DateField()
  birth_place = md.CharField(max_length=20)
  address = md.TextField(blank=False)
  created_at = md.DateTimeField(auto_now_add=True)
  updated_at = md.DateTimeField(auto_now=True)

