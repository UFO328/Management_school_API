from django.db import models as md 
from .teacher_model import Teacher 

class TeacherProfile(md.Model):
  teacher = md.OneToOneField(Teacher,on_delete=md.PROTECT,related_name='teacher_profile')
  email = md.EmailField()
  phone = md.CharField(max_length=13)
  address = md.TextField(blank=True)
  