from student.models import Student 
from django.db import transaction

class StudentServices:
  def __init__(self,intances):
    self.intances = intances

  def update_student(self):
    with transaction.atomic():
      student = Student.objects.select_for_update().get(pk=self.intances.pk)
      pass