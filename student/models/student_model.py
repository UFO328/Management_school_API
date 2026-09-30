from django.db import models as md 


class Student(md.Model):
  class GenderChoice(md.TextChoices):
    pria = "pria","Pria"
    wanita = "wanita","Wanita"
  class StatusChoice(md.TextChoices):
    active = "active","Active"
    transfer = "transfer","Transfer"
    drop_out = "drop out","Drop Out"
    no_have_class = "no have class","No Have Class"
    
  fullname = md.CharField(max_length=255,null=False,blank=False)
  nik = md.CharField(max_length=30,unique=True,null=False,blank=False)
  nis = md.CharField(max_length=10, unique=True, null=True, blank=True, default=None)
  nisn = md.CharField(max_length=16,unique=True,null=False,blank=False)
  gender = md.CharField(max_length=10,choices=GenderChoice.choices)
  status = md.CharField(max_length=80,choices=StatusChoice.choices)
  is_active = md.BooleanField(default=True)
  created_at = md.DateTimeField(auto_now_add=True)
  updated_at = md.DateTimeField(auto_now=True)
  