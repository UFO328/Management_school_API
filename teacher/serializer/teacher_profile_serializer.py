from rest_framework import serializers as sz 
from .serializer_output import TeacherOutputSerializer
from ..models import TeacherProfile,Teacher

class TeacherProfileSerializer(sz.ModelSerializer):
  #untuk method get
  teacher = TeacherOutputSerializer(read_only=True)

  #untuk method post,pacth,put
  teacher_id = sz.PrimaryKeyRelatedField(source="teacher",queryset=Teacher.objects.all(),write_only=True)

  class Meta:
    model = TeacherProfile
    fields = "__all__"

  def validate(self, attrs):
    teacher = attrs.get("teacher", getattr(self.instance, "teacher", None))
    if teacher is None:
      return attrs
    qs = TeacherProfile.objects.filter(teacher=teacher)
    if self.instance:
      qs = qs.exclude(pk=self.instance.pk)
    if qs.exists():
      raise sz.ValidationError({"teacher_id": "teacher ini sudah memiliki profil."})
    return attrs