from rest_framework import viewsets as vw
from rest_framework import serializers as sz
from drf_spectacular.utils import (
  extend_schema_view, extend_schema, OpenApiExample, inline_serializer
)
from ..serializer import TeacherProfileSerializer
from ..models import TeacherProfile
from core.permission import SchoolModelPermissions

_teacher_profile_validation_error_400 = inline_serializer(
  name="TeacherProfileValidationError400",
  fields={
    "teacher_id": sz.ListField(child=sz.CharField(), required=False),
    "email": sz.ListField(child=sz.CharField(), required=False),
    "phone": sz.ListField(child=sz.CharField(), required=False),
    "address": sz.ListField(child=sz.CharField(), required=False),
  }
)

@extend_schema_view(
  list=extend_schema(
    summary="List semua teacher profile",
    description=(
      "Daftar profile guru terurut ascending berdasarkan `id`, "
      "dipaginasi (20 data per halaman, query parameter `page`). "
      "Response menyertakan objek `teacher` (read-only, nested). "
      "Memerlukan permission `teacher.view_teacherprofile`."
    ),
    tags=["Teacher Profile"],
  ),
  create=extend_schema(
    summary="Buat teacher profile baru",
    description=(
      "Membuat profile untuk satu guru. Kirim `teacher_id` (write-only) "
      "pada request; field `teacher` pada response bersifat read-only/nested. "
      "Satu guru hanya boleh memiliki satu profile (one-to-one). "
      "`phone` maksimal 13 karakter, `address` opsional. "
      "Memerlukan permission `teacher.add_teacherprofile`."
    ),
    tags=["Teacher Profile"],
    responses={
      201: TeacherProfileSerializer,
      400: _teacher_profile_validation_error_400,
    },
    examples=[
      OpenApiExample(
        name="Request Valid",
        value={
          "teacher_id": 1,
          "email": "andi.wijaya@mail.com",
          "phone": "08123456789",
          "address": "Jl. Contoh No. 1, Bandung",
        },
        request_only=True,
      ),
      OpenApiExample(
        name="Response Sukses",
        value={
          "id": 1,
          "teacher": {"id": 1, "fullname": "Andi Wijaya"},
          "email": "andi.wijaya@mail.com",
          "phone": "08123456789",
          "address": "Jl. Contoh No. 1, Bandung",
        },
        response_only=True,
        status_codes=["201"],
      ),
      OpenApiExample(
        name="Error - guru sudah punya profile",
        value={"teacher_id": ["teacher ini sudah memiliki profil."]},
        response_only=True,
        status_codes=["400"],
      ),
      OpenApiExample(
        name="Error - teacher_id tidak ditemukan",
        value={"teacher_id": ['Invalid pk "999" - object does not exist.']},
        response_only=True,
        status_codes=["400"],
      ),
    ],
  ),
  retrieve=extend_schema(
    summary="Detail teacher profile",
    description=(
      "Mengembalikan satu profile beserta objek `teacher` (nested). "
      "Memerlukan permission `teacher.view_teacherprofile`."
    ),
    tags=["Teacher Profile"],
  ),
  update=extend_schema(
    summary="Update penuh teacher profile (PUT)",
    description=(
      "Mengganti seluruh data profile. "
      "Gunakan `teacher_id` (write-only) untuk mengganti guru terkait. "
      "Memerlukan permission `teacher.change_teacherprofile`."
    ),
    tags=["Teacher Profile"],
    responses={
      200: TeacherProfileSerializer,
      400: _teacher_profile_validation_error_400,
    },
  ),
  partial_update=extend_schema(
    summary="Update sebagian teacher profile (PATCH)",
    description=(
      "Mengubah hanya field yang dikirim. "
      "Memerlukan permission `teacher.change_teacherprofile`."
    ),
    tags=["Teacher Profile"],
    responses={
      200: TeacherProfileSerializer,
      400: _teacher_profile_validation_error_400,
    },
  ),
  destroy=extend_schema(
    summary="Hapus teacher profile",
    description=(
      "Menghapus profile berdasarkan `id` (tidak menghapus guru-nya). "
      "Memerlukan permission `teacher.delete_teacherprofile`."
    ),
    tags=["Teacher Profile"],
    responses={204: None},
  ),
)
class TeacherProfileViewSet(vw.ModelViewSet):
  serializer_class = TeacherProfileSerializer
  permission_classes = [SchoolModelPermissions]

  def get_queryset(self):
    return TeacherProfile.objects.select_related("teacher").order_by("id")
