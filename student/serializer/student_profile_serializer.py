from rest_framework import serializers as sz 
from ..models import Student,StudentProfile
from .serializer_output import StudentOutputSerializer


class StudentProfileSerializer(sz.ModelSerializer):
  student = StudentOutputSerializer(read_only=True)
  student_id = sz.PrimaryKeyRelatedField(queryset=Student.objects.all(),source="student",write_only=True)

  class Meta:
    model = StudentProfile
    fields = ['id','student','student_id','email','phone','birth_date','birth_place','address']

  def validate(self, attrs):
    student = attrs.get("student", getattr(self.instance, "student", None))
    if student is None:
      return attrs
    qs = StudentProfile.objects.filter(student=student)
    if self.instance:
      qs = qs.exclude(pk=self.instance.pk)
    if qs.exists():
      raise sz.ValidationError({"student_id": "Student ini sudah memiliki profil."})
    return attrs