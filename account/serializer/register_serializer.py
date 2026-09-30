from django.contrib.auth.models import User 
from rest_framework import serializers as sz 

class RegisterSerializer(sz.Serializer):
  username = sz.CharField()
  email = sz.EmailField()
  password = sz.CharField(write_only=True)

  def validate_password(self,pw):
    if len(pw) < 8:
      raise sz.ValidationError("Minimal Password 8 Character")
    return pw 

  def validate_username(self,username):
    if User.objects.filter(username=username).exists():
      raise sz.ValidationError("Username Tidak Tersedia")
    return username

  def validate_email(self,email):
    if User.objects.filter(email=email).exists():
      raise sz.ValidationError("Email Tidak Tersedia")
    return email 
    
  def create(self,validate_data):
    user = User.objects.create_user(
      username=validate_data["username"],
      email=validate_data["email"],
      password=validate_data["password"],
    )
    return user