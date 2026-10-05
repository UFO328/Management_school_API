from rest_framework import viewsets as vw
from rest_framework import serializers as sz
from drf_spectacular.utils import (
  extend_schema_view, extend_schema, OpenApiExample, inline_serializer
)
from ..serializer import StudentProfileSerializer
from ..models import StudentProfile
from core.permission import SchoolModelPermissions

_student_profile_validation_error_400 = inline_serializer(
  name="StudentProfileValidationError400",
  fields={
    "student_id": sz.ListField(child=sz.CharField(), required=False),
    "email": sz.ListField(child=sz.CharField(), required=False),
    "phone": sz.ListField(child=sz.CharField(), required=False),
    "birth_date": sz.ListField(child=sz.CharField(), required=False),
    "birth_place": sz.ListField(child=sz.CharField(), required=False),
    "address": sz.ListField(child=sz.CharField(), required=False),
  }
)

@extend_schema_view(
  list=extend_schema(
    summary="List semua student profile",
    description=(
      "Daftar profile siswa terurut descending berdasarkan `id`, "
      "dipaginasi (20 data per halaman, query parameter `page`). "
      "Response menyertakan objek `student` (read-only, nested). "
      "Memerlukan permission `student.view_studentprofile`."
    ),
    tags=["Student Profile"],
  ),
  create=extend_schema(
    summary="Buat student profile baru",
    description=(
      "Membuat profile untuk satu student. Kirim `student_id` (write-only) "
      "pada request; field `student` pada response bersifat read-only/nested. "
      "Satu student hanya boleh memiliki satu profile (one-to-one). "
      "`phone` maksimal 14 karakter. "
      "Memerlukan permission `student.add_studentprofile`."
    ),
    tags=["Student Profile"],
    responses={
      201: StudentProfileSerializer,
      400: _student_profile_validation_error_400,
    },
    examples=[
      OpenApiExample(
        name="Request Valid",
        value={
          "student_id": 1,
          "email": "budi.santoso@mail.com",
          "phone": "081234567890",
          "birth_date": "2008-01-15",
          "birth_place": "Jakarta",
          "address": "Jl. Contoh No. 1, Jakarta",
        },
        request_only=True,
      ),
      OpenApiExample(
        name="Response Sukses",
        value={
          "id": 1,
          "student": {
            "id": 1,
            "fullname": "Budi Santoso",
            "nis": "1001",
            "nik": "3201011501900001",
            "nisn": "0012345678",
            "gender": "pria",
            "status": "active",
            "is_active": True,
          },
          "email": "budi.santoso@mail.com",
          "phone": "081234567890",
          "birth_date": "2008-01-15",
          "birth_place": "Jakarta",
          "address": "Jl. Contoh No. 1, Jakarta",
        },
        response_only=True,
        status_codes=["201"],
      ),
      OpenApiExample(
        name="Error - student sudah punya profile",
        value={"student_id": ["Student ini sudah memiliki profil."]},
        response_only=True,
        status_codes=["400"],
      ),
      OpenApiExample(
        name="Error - student_id tidak ditemukan",
        value={"student_id": ['Invalid pk "999" - object does not exist.']},
        response_only=True,
        status_codes=["400"],
      ),
    ],
  ),
  retrieve=extend_schema(
    summary="Detail student profile",
    description=(
      "Mengembalikan satu profile beserta objek `student` (nested). "
      "Memerlukan permission `student.view_studentprofile`."
    ),
    tags=["Student Profile"],
  ),
  update=extend_schema(
    summary="Update penuh student profile (PUT)",
    description=(
      "Mengganti seluruh data profile, semua field wajib dikirim. "
      "Gunakan `student_id` (write-only) untuk mengganti student terkait. "
      "Memerlukan permission `student.change_studentprofile`."
    ),
    tags=["Student Profile"],
    responses={
      200: StudentProfileSerializer,
      400: _student_profile_validation_error_400,
    },
  ),
  partial_update=extend_schema(
    summary="Update sebagian student profile (PATCH)",
    description=(
      "Mengubah hanya field yang dikirim. "
      "Memerlukan permission `student.change_studentprofile`."
    ),
    tags=["Student Profile"],
    responses={
      200: StudentProfileSerializer,
      400: _student_profile_validation_error_400,
    },
  ),
  destroy=extend_schema(
    summary="Hapus student profile",
    description=(
      "Menghapus profile berdasarkan `id` (tidak menghapus student-nya). "
      "Memerlukan permission `student.delete_studentprofile`."
    ),
    tags=["Student Profile"],
    responses={204: None},
  ),
)
class StudentProfileViewSet(vw.ModelViewSet):
  serializer_class = StudentProfileSerializer
  permission_classes = [SchoolModelPermissions]

  def get_queryset(self):
    return StudentProfile.objects.select_related("student").order_by("-id")
