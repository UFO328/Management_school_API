from django.contrib.auth.models import User 
from rest_framework import serializers as sz 
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class RegisterSerializer(sz.Serializer):
  username = sz.CharField(max_length=150)
  email = sz.EmailField(max_length=254)
  password = sz.CharField(write_only=True)

  def validate_password(self,pw):
    try:
      validate_password(pw,User(username=username))
      return pw 
    except ValidationError as e:
      raise sz.ValidationError(e.messages)
      
  def validate_username(self,username):
    if User.objects.filter(username=username).exists():
      raise sz.ValidationError("Username Tidak Tersedia")

    if len(username) < 7:
      raise sz.ValidationError("Username Terlalu Pendek")
      
    return username

  def validate_email(self,email):
    if User.objects.filter(email=email).exists():
      raise sz.ValidationError("Email Tidak Tersedia")
    return email 
    
  def create(self,validate_data):
    #user yang baru buat akun sengaja aku belum
    #kasih group karena nanti pembuatan akun ada 
    #di admin dan penentuan group ada di admin 
    #sekarang desain sytem nya dalam tahap pengembangan
    user = User.objects.create_user(
        username=validate_data["username"],
        email=validate_data["email"],
        password=validate_data["password"],
      )
    user.full_clean()
    
    return user
