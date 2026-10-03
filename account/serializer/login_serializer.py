from rest_framework import serializers as sz 
from django.contrib.auth import authenticate 

class LoginSerializer(sz.Serializer):
  username = sz.CharField()
  password = sz.CharField(write_only=True)

  def validate(self,data):
    username = data["username"]
    password = data["password"]

    request = self.context.get("request")
    user = authenticate(request,username=username,password=password)

    if not user:
      raise sz.ValidationError("Username Atau Password Salah")

    
    data["user"] = user 
    return data
      
      