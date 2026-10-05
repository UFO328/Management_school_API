from rest_framework import viewsets as vw
from rest_framework import serializers as sz
from core.permission import SchoolModelPermissions
from rest_framework.exceptions import ValidationError
from django.db.models import ProtectedError
from drf_spectacular.utils import (
  extend_schema_view, extend_schema, OpenApiExample, inline_serializer
)
from ..serializer import StudentSerializer
from ..models import Student

_student_validation_error_400 = inline_serializer(
  name="StudentValidationError400",
  fields={
    "fullname": sz.ListField(child=sz.CharField(), required=False),
    "nik": sz.ListField(child=sz.CharField(), required=False),
    "nis": sz.ListField(child=sz.CharField(), required=False),
    "nisn": sz.ListField(child=sz.CharField(), required=False),
    "gender": sz.ListField(child=sz.CharField(), required=False),
    "status": sz.ListField(child=sz.CharField(), required=False),
    "is_active": sz.ListField(child=sz.CharField(), required=False),
  }
)

_student_protected_delete_400 = inline_serializer(
  name="StudentProtectedDelete400",
  fields={"detail": sz.CharField()}
)

@extend_schema_view(
  list=extend_schema(
    summary="List semua student",
    description=(
      "Daftar student terurut ascending berdasarkan `fullname`, "
      "dipaginasi (20 data per halaman, query parameter `page`). "
      "Memerlukan permission `student.view_student`."
    ),
    tags=["Student"],
  ),
  create=extend_schema(
    summary="Buat student baru",
    description=(
      "Membuat data student. `nik` dan `nisn` wajib unik, `nis` opsional "
      "(boleh null), `is_active` default `true`. "
      "Memerlukan permission `student.add_student`."
    ),
    tags=["Student"],
    responses={
      201: StudentSerializer,
      400: _student_validation_error_400,
    },
    examples=[
      OpenApiExample(
        name="Request Valid",
        value={
          "fullname": "Budi Santoso",
          "nik": "3201011501900001",
          "nis": "1001",
          "nisn": "0012345678",
          "gender": "pria",
          "status": "active",
          "is_active": True,
        },
        request_only=True,
      ),
      OpenApiExample(
        name="Response Sukses",
        value={
          "id": 1,
          "fullname": "Budi Santoso",
          "nik": "3201011501900001",
          "nis": "1001",
          "nisn": "0012345678",
          "gender": "pria",
          "status": "active",
          "is_active": True,
          "created_at": "2026-10-04T08:00:00Z",
          "updated_at": "2026-10-04T08:00:00Z",
        },
        response_only=True,
        status_codes=["201"],
      ),
      OpenApiExample(
        name="Error - NIK sudah dipakai",
        value={"nik": ["student with this nik already exists."]},
        response_only=True,
        status_codes=["400"],
      ),
      OpenApiExample(
        name="Error - status tidak valid",
        value={"status": ['"nonactive" is not a valid choice.']},
        response_only=True,
        status_codes=["400"],
      ),
    ],
  ),
  retrieve=extend_schema(
    summary="Detail student",
    description=(
      "Mengembalikan satu student berdasarkan `id`. "
      "Memerlukan permission `student.view_student`."
    ),
    tags=["Student"],
  ),
  update=extend_schema(
    summary="Update penuh student (PUT)",
    description=(
      "Mengganti seluruh data student, semua field wajib dikirim. "
      "Memerlukan permission `student.change_student`."
    ),
    tags=["Student"],
    responses={
      200: StudentSerializer,
      400: _student_validation_error_400,
    },
  ),
  partial_update=extend_schema(
    summary="Update sebagian student (PATCH)",
    description=(
      "Mengubah hanya field yang dikirim. "
      "Memerlukan permission `student.change_student`."
    ),
    tags=["Student"],
    responses={
      200: StudentSerializer,
      400: _student_validation_error_400,
    },
  ),
  destroy=extend_schema(
    summary="Hapus student",
    description=(
      "Menghapus student. Jika student masih memiliki `StudentProfile`, "
      "penghapusan ditolak karena `on_delete=PROTECT` dan mengembalikan 400. "
      "Memerlukan permission `student.delete_student`."
    ),
    tags=["Student"],
    responses={
      204: None,
      400: _student_protected_delete_400,
    },
    examples=[
      OpenApiExample(
        name="Error - masih memiliki profile",
        value={"detail": "User Ini masih Memiliki Profile"},
        response_only=True,
        status_codes=["400"],
      ),
    ],
  ),
)
class StudentViewSet(vw.ModelViewSet):
  serializer_class = StudentSerializer
  permission_classes = [SchoolModelPermissions]

  def get_queryset(self):
    return Student.objects.all().order_by("fullname")

  def perform_destroy(self,intances):
    try:
      intances.delete()
    except ProtectedError:
      raise ValidationError({"detail":"User Ini masih Memiliki Profile"})
