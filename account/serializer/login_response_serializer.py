from rest_framework import serializers

# Serializer output biar kebaca Swagger
class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user_role = serializers.ListField(child=serializers.CharField())
    user_id = serializers.IntegerField()
    username = serializers.CharField()