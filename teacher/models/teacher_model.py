from django.db import models as md 


class Teacher(md.Model):
  class StatusChoice(md.TextChoices):
    active = "active","Active"
    transfer = "transfer","Transfer"
    cut_off = "cut off","Cut Off"
  fullname = md.CharField(max_length=255,null=False,blank=False)
  nik = md.CharField(max_length=30,unique=True,null=False,blank=False)
  status = md.CharField(max_length=80,choices=StatusChoice.choices)
  is_active = md.BooleanField(default=True)
  created_at = md.DateTimeField(auto_now_add=True)
  updated_at = md.DateTimeField(auto_now=True)
  
  