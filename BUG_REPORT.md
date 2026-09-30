# Laporan Bug — SMK Kharya Bhakti API (Django REST Framework)

Tanggal audit: 2026-09-30
Target: `managemant_school` (Django 6.1, DRF 3.18, drf-spectacular, PostgreSQL)

Semua temuan di bawah **sudah diverifikasi dengan reproduksi** terhadap database
dev yang sedang berjalan (test diletakkan di dalam transaction + rollback,
tidak ada data yang berubah). Tidak ada file yang diubah selain dokumen ini.

---

## Ringkasan

| # | Severity | Lokasi | Ringkasan |
|---|----------|--------|-----------|
| 1 | CRITICAL | `managemant_school/settings.py:31` | `ALLOWED_HOSTS = []` → 400 DisallowedHost di host mana pun selain localhost |
| 2 | CRITICAL | `student/models/student_model.py:16` | `nis` `unique=True` + `blank=True` → student ke-2 tanpa NIS **500** |
| 3 | CRITICAL | `student/serializer/student_profile_serializer.py:8`, `teacher/serializer/teacher_profile_serializer.py:10` | Field OneToOne tanpa `UniqueValidator` → **500** IntegrityError, dan PATCH bisa "mencuri" profil student lain |
| 4 | CRITICAL | `.env` (root) | `SECRET_KEY` + password DB tersimpan, tidak ada `.gitignore`, tidak ada `requirements.txt` |
| 5 | HIGH | `account/serializer/login_serializer.py:12` | `self.context.get("context")` → `request` selalu `None` saat `authenticate()` |
| 6 | HIGH | `core/permission/student_view_permission.py:34` | `return []` untuk method lain → permission bypass pada `OPTIONS`/`HEAD` |
| 7 | HIGH | `managemant_school/settings.py:29,92,93` | `DEBUG=True`, `SESSION_COOKIE_SECURE=False`, `CSRF_COOKIE_SECURE=False` hardcode |
| 8 | HIGH | `account/views/login_viewset.py` | Tidak ada throttling (brute force) dan tidak ada endpoint logout |
| 9 | HIGH | group `ADMIN` di DB | Tidak punya permission `studentprofile` → **403** di `/student/school/api/student-profile/` |
| 10 | MEDIUM | `managemant_school/settings.py:182` | `MAILERS` bukan setting Django (salah nama, harus `EMAIL_BACKEND`) |
| 11 | MEDIUM | `student/serializer/serializer_output/student_output_serializer.py:8` | `fields` duplikat `"nis"` dua kali → `nik` tidak pernah dikirim |
| 12 | MEDIUM | `managemant_school/settings.py` | `SPECTACULAR_SETTINGS` tidak ada → judul API kosong; `schema.yaml` hasil generate yang diedit manual (akan hilang saat regenerate) |
| 13 | MEDIUM | `account/serializer/register_serializer.py` | Password validator Django tidak dipakai, email tidak dinormalisasi |
| 14 | MEDIUM | `account/views/register_viewset.py:70` | User hasil register tidak masuk group mana pun → 403 di semua endpoint |
| 15 | MEDIUM | `teacher/migrations/0003_teacher_status.py:16` | `default='Active'` tidak ada di dalam `choices` (`active`) |
| 16 | MEDIUM | `student/views/student_viewset.py:14` | Tidak ada pagination + `print()` debug di dalam `list()` |
| 17 | MEDIUM | `teacher/models/teacher_profile_model.py:5` | `related_name='teacher'` membuat `teacher.teacher` ambigu |
| 18 | LOW | `student/models/studentProfile_model.py:6`, `teacher/models/teacher_profile_model.py:6` | `email` tidak unik |
| 19 | LOW | `core/permission/student_view_permission.py:6`, `account/views/login_viewset.py:64` | `print()` debug membocorkan session key ke log server |
| 20 | LOW | `account/serializer/login_serializer.py:18` | `if not user.is_active` dead code (tidak pernah tercapai) |
| 21 | LOW | paket & struktur | `academic` tidak terdaftar di `INSTALLED_APPS`, banyak `__init__.py` hilang, `docs/` kosong, nol test |
| 22 | LOW | beberapa | import tidak terpakai, typo `intances`, service method kosong |

---

## CRITICAL

### 1. `ALLOWED_HOSTS = []` — API menolak semua host selain localhost

**Masalah**
`managemant_school/settings.py:31` bernilai `[]`. Dengan `DEBUG = True`, Django
fallback ke `['.localhost', '127.0.0.1', '[::1]']`. Host lain (IP LAN, domain
produksi, `testserver`) ditolak.

**Penyebab**
List kosong; komentar di `settings.py:60` (`#ALLOWED_HOSTS = ["*"] # buat dev aja`)
menunjukkan daftar host memang belum pernah diisi.

**Dampak**
Reproduksi: `Client()` (host `testserver`) → `django.core.exceptions.DisallowedHost:
Invalid HTTP_HOST header: 'testserver'` → **HTTP 400** untuk seluruh request.
Konsekuensi: mustahil diakses dari perangkat lain di jaringan yang sama, dan
`manage.py runserver 0.0.0.0:8000` tidak bisa dipakai untuk testing di HP.

**Solusi**
```python
import os
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
if not DEBUG:
    ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("ALLOWED_HOSTS wajib diisi saat DEBUG=False")
```
Domain produksi dibaca dari `.env`, bukan di-hardcode.

---

### 2. `Student.nis` `unique=True` + `blank=True` → 500 saat membuat student kedua tanpa NIS

**Masalah**
`student/models/student_model.py:16`:
```python
nis = md.CharField(max_length=10, unique=True, null=False, blank=True)
```
Kolom `unique=True` tetapi boleh kosong. Student pertama tanpa NIS disimpan
sebagai string kosong `''`. Student kedua tanpa NIS akan melanggar unique constraint.

**Penyebab**
`blank=True` hanya mengatur validasi level form/serializer, tidak mengubah nilai
yang disimpan ke database. Karena `null=False`, Django menyimpan `''`, bukan `NULL`.
PostgreSQL tidak mengabaikan unique constraint untuk `''`.

**Dampak**
Reproduksi (superuser, endpoint `POST /student/school/api/student/`):
```
POST student #1 (nis tidak dikirim): 201 Created
POST student #2 (nis tidak dikirim): 500 Internal Server Error
django.db.utils.IntegrityError: duplicate key value violates unique constraint "student_student_nis_key"
DETAIL:  Key (nis)=() already exists.
```
Efek: hanya **satu** siswa yang boleh ber-NIS kosong. Request kedua kena 500, dan
`TransactionManagementError`arringenerated. Data bulan lalu saya tidak tersisa
(rollback).NIS praktis selalu diisi di sekolah, tapi field ini sengaja opsional
(`nis` tidak ada di `required` OpenAPI), jadi ini bom waktu di produksi.

**Solusi**
Pilihan terbaik — jadikan opsional tapi tetap unik secara aman:
```python
nis = models.CharField(max_length=10, unique=True, null=True, blank=True, default=None)
```
Lalu migration:
```python
migrations.RunSQL(
    sql='UPDATE student_student SET nis = NULL WHERE nis = %s;',
    params=[''],
    reverse_sql=migrations.RunSQL.noop,
),
migrations.AlterField(
    model_name='student', name='nis',
    field=models.CharField(blank=True, default=None, max_length=10, null=True, unique=True),
),
```
Alternatif (kalau NIS memang wajib): ubah ke `blank=False, null=False` dan
tambahkan `nis` ke daftar `required` serializer.

---

### 3. Field OneToOne pada serializer tidak punya validasi keunikan → 500 & pencurian data profil

**Masalah**
`student/serializer/student_profile_serializer.py:8`
`teacher/serializer/teacher_profile_serializer.py:10`
```python
student_id = sz.PrimaryKeyRelatedField(queryset=Student.objects.all(), source="student", write_only=True)
teacher_id = sz.PrimaryKeyRelatedField(queryset=Teacher.objects.all(),  source="teacher",  write_only=True)
```
Karena field ini **dideklarasikan manual**, DRF tidak lagi menambahkan
`UniqueValidator` otomatis pada field OneToOne model. Hasilnya serializer
`is_valid()` selalu `True`, lalu `IntegrityError` terjadi saat `.save()`.

**Penyebab**
Aturan DRF: `UniqueValidator` hanya diinferensikan otomatis bila field
OneToOne **tidak** dideklarasikan eksplisit di serializer.

**Dampak**
Reproduksi (superuser):
```
POST /student-profile/ dengan student_id yang sudah punya profil : 500   (harusnya 400)
POST /teacher-profile/ dengan teacher_id yang sudah punya profil : 500   (harusnya 400)
PATCH /student-profile/{id}/ {"student_id": <student lain>}      : 200   (harusnya 400)
```
Dua dampak berbeda:
1. **500 error** untuk duplikat — membingungkan frontend, tidak ada pesan validasi.
2. **Data integrity rusak**: `PATCH` dengan `student_id` milik siswa lain berhasil
   200 dan diam-diam memindahkan profil dari siswa A ke siswa B. Setelah itu siswa A
   tidak punya profil dan siswa B justru punya dua. Saya buktikan di DB: `PATCH` mengubah
   `student_id` dari siswa Q1 ke Q2 dengan status 200.

**Solusi**
```python
class StudentProfileSerializer(sz.ModelSerializer):
    student = StudentOutputSerializer(read_only=True)
    student_id = sz.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source="student", write_only=True
    )

    class Meta:
        model = StudentProfile
        fields = ['student', 'student_id', 'email', 'phone',
                  'birth_date', 'birth_place', 'address']
        validators = [UniqueTogetherValidator(...)]

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
```
Terapkan pola identik pada `TeacherProfileSerializer`. Bila relasi ini tidak pernah
berubah setelah dibuat, lebih aman: `read_only=True` pada `student_id` untuk `PATCH`
dan `create()` dipanggil dari action khusus.

---

### 4. Kredensial bocor di dalam folder project, tidak ada `.gitignore`, tidak ada `requirements.txt`

**Masalah**
File `.env` di root berisi:
```
db_pw="admin123"
SECRET_KEY='django-insecure-!rwq00(k110xgd%535q+lxb&96u^n6m-4aen(w5lp#lj_(1kvb'
```
Tidak ada `.gitignore`. Tidak ada `requirements.txt`. `SECRET_KEY` masih pakai
prefix `django-insecure-`.

**Penyebab**
`.env` dibuat manual tanpa di-ignore, dan dependency tidak pernah di-pin.

**Dampak**
- Kalau folder ini masuk git (atau di-backup/di-share), password database dan
  `SECRET_KEY` ikut terbawa. `SECRET_KEY` yang bocor = session/cookie bisa
  dipalsukan (session hijacking, `CSRF_COOKIE` forging).
- Tidak ada daftar dependency → mustahil deploy reproducibly. Contoh: `corsheaders`
  dan `python-dotenv` dipakai di `settings.py` tapi tidak tercatat versi.
- `MAILERS`/`EMAIL_BACKEND` tidak ada konfigurasi cadangan karena `requirements.txt` kosong.

**Solusi**
1. Buat `.gitignore`:
   ```gitignore
   .env
   __pycache__/
   *.py[cod]
   db.sqlite3
   schema.yaml
   ```
   (`schema.yaml` ikut di-ignore karena itu file generate — lihat temuan 12.)
2. Buat `.env.example` dengan placeholder, tanpa nilai asli.
3. `pip freeze > requirements.txt` (pinned), pisahkan `requirements-dev.txt` bila perlu.
4. Generate `SECRET_KEY` baru yang production-grade:
   ```python
   python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
   ```
   Simpan di `.env`/secret manager, **jangan** di dalam repository.
5. Ganti password database yang sudah tertulis di `.env`.

---

## HIGH

### 5. `authenticate()` dipanggil tanpa `request` pada login

**Masalah**
`account/views/login_viewset.py:58` mengirim `context={'request': request}`,
tetapi `account/serializer/login_serializer.py:12` membaca `self.context.get("context")`.

**Penyebab**
Typo nama key: `"context"` seharusnya `"request"`. `dict.get()` diam-dmengembalikan
`None`, tidak melempar error.

**Dampak**
`authenticate(None, username=..., password=...)`. Login tetap terlihat "berhasil"
karena `django.contrib.auth.authenticate()` membuat `HttpRequest()` kosong otomatis
dan `ModelBackend` kebetulan tidak butuh `request`. Jadi bug ini **tersembunyi**:

- Custom backend yang butuh `request` (membaca header, IP untuk rate-limit,
  lockout di `request.session`) akan salah atau crash.
- `authenticate()` tidak bisa dibatasi per-IP.
- Tidak ada jejak di log bahwa request aslinya hilang.

**Solusi**
```python
def validate(self, data):
    request = self.context.get("request")
    if request is None:
        raise sz.ValidationError("Request context tidak tersedia.")
    user = authenticate(request, username=data["username"], password=data["password"])
    ...
```

---

### 6. Permission bypass pada `OPTIONS` dan `HEAD`

**Masalah**
`core/permission/student_view_permission.py:22-35` — `get_required_permissions()`
hanya menangani GET/POST/PUT/PATCH/DELETE; sisanya jatuh ke `return []`.
`DjangoModelPermissions` akan menganggap "tidak butuh permission" → lolos.

**Penyebab**
Tidak ada fallback yang menolak request dengan method tak dikenal.

**Dampak**
Reproduksi dengan user yang **tidak punya permission sama sekali**:
```
GET    /student/school/api/student/  -> 403   (benar)
POST   /student/school/api/student/  -> 403   (benar)
OPTIONS /student/school/api/student/ -> 200   (BUG)
HEAD   /student/school/api/student/  -> 200   (BUG)
```
`OPTIONS` membocorkan metadata endpoint (nama field serializer, daftar method yang
diizinkan, metadata filter/bisa paginasi) tanpa permission. Policy keamanan jadi
tidak konsisten antar-method, dan audit permission jadi menyesatkan.

**Solusi**
```python
from rest_framework.permissions import SAFE_METHODS

def get_required_permissions(self, method, model_cls):
    opts = model_cls._meta
    if method in SAFE_METHODS:
        action = "view" if method in ("GET", "HEAD", "OPTIONS") else "add"
    elif method == "POST":
        action = "add"
    elif method in ("PUT", "PATCH"):
        action = "change"
    elif method == "DELETE":
        action = "delete"
    else:
        return [f"{opts.app_label}.nonexistent_{method.lower()}"]  # selalu ditolak
    return [f"{opts.app_label}.{action}_{opts.model_name}"]
```
Alternatif yang lebih aman: whitelist method, lalu `raise MethodNotAllowed` untuk
method lain di level view.

---

### 7. `DEBUG = True` dan cookie tidak di-secure — hardcode

**Masalah**
`managemant_school/settings.py:29` `DEBUG = True`;
`:92` `SESSION_COOKIE_SECURE = False`; `:93` `CSRF_COOKIE_SECURE = False`.

**Penyebab**
Nilai ditetapkan langsung, tidak dari environment.

**Dampak**
- Di produksi (`DEBUG=True`): setiap exception menampilkan **traceback lengkap +
  nilai variabel lokal + seluruh `settings` (termasuk `SECRET_KEY`, `db_pw`)**.
  Informasi yang biasanya tersembunyi di dalam halaman error — seperti bug #3 dan #5 — akan ikut membocorkan kredensial DB.
- `SESSION_COOKIE_SECURE=False` → cookie session terkirim lewat HTTP biasa, bisa
  dicuri di jaringan (sesi perawan).
- `SESSION_COOKIE_SAMESITE = "Lax"` juga hardcode; saat frontend dipindah ke domain
  berbeda, cookie tidak akan terkirim sama sekali (gejala: login sukses lalu
  endpoint berikutnya 403).

**Solusi**
```python
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

SESSION_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_SECURE      = not DEBUG
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE    = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY    = False          # wajib False untuk SPA JS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # hanya di belakang proxy
```
`.env` produksi:
```
DEBUG=False
ALLOWED_HOSTS=api.sekolah.sch.id
SESSION_COOKIE_SAMESITE=None            # hanya jika lintas-site memang diperlukan
CSRF_TRUSTED_ORIGINS=https://app.sekolah.sch.id
CORS_ALLOWED_ORIGINS=https://app.sekolah.sch.id
```
`CSRF_TRUSTED_ORIGINS` (`:63`) dan `CORS_ALLOWED_ORIGINS` (`:68`) juga hanya
memuat `http://127.0.0.1:5500` dan `http://localhost:5500` — keduanya wajib
dipindah ke domain asli saat deploy.

---

### 8. Login tanpa rate limit, dan tidak ada endpoint logout

**Masalah**
Tidak ada `DEFAULT_THROTTLE_CLASSES` di `settings.py:52` dan tidak ada throttle di
view. `account/urls.py` hanya punya `login/`, `register/`, `csrf/` — **tidak ada
`logout/`**.

**Penyebab**
Fitur throttle dan logout belum pernah dibuat.

**Dampak**
- Brute force: `POST /auth/school/api/login/` bisa dicoba thousands of times per
  menit tanpa penalty. Database dipanggil tiap percobaan (`authenticate()` → query
  User) → risiko resource exhaustion.
- Tidak ada cara mengakhiri sesi dari sisi client. Satu-satunya cara adalah
  menunggu `SESSION_COOKIE_AGE` (30 menit) atau dihapus dari sisi server. Untuk
  shared device atau akun yang dikompromikan, ini bermasalah.
- Login juga tidak memaksa rotasi `csrf_token` untuk proteksi login-CSRF
  (pola "login CSRF" — penyerang bisa memaksa korban masuk ke akun penyerang).

**Solusi**
```python
REST_FRAMEWORK = {
    ...,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '120/min',
        'login': '10/min',
    },
}
```
```python
class LoginAPIView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
```
Tambahkan endpoint logout:
```python
@extend_schema(request=None, responses={204: None})
def post(self, request):
    from django.contrib.auth import logout
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)
```
```python
path("logout/", LogoutAPIView.as_view(), name="logout"),
```

---

### 9. Group `ADMIN` tidak punya permission `studentprofile` → 403

**Masalah**
Isi group `ADMIN` saat ini:
```
add_student, change_student, delete_student, view_student,
add_teacher, change_teacher, delete_teacher, view_teacher,
add_teacherprofile, change_teacherprofile, delete_teacherprofile, view_teacherprofile
```
`studentprofile` **tidak ada**.

**Penyebab**
Model `StudentProfile` ditambahkan/diubah setelah permission group dibuat, dan
permission group tidak pernah di-refresh.

**Dampak**
Reproduksi sebagai user dalam group `ADMIN`:
```
GET  /student/school/api/student/          -> 200
GET  /teacher/school/api/teacher/          -> 200
GET  /teacher/school/api/teacher-profile/  -> 200
GET  /student/school/api/student-profile/  -> 403   <-- BUG
POST /student/school/api/student-profile/  -> 403   <-- BUG
```
User yang secara bisnis berhak mengelola siswa tidak bisa melihat profil siswa mana
pun. Group `STAFF` bahkan **tidak punya permission apa pun** (`perms: []`), dan
`eko` + `riski2` **tidak punya group sama sekali** — hasil register otomatis.

**Solusi**
Jangan ubah lewat SQL. Buat data permission sebagai bagian dari migration
`account/migrations/` sehingga idempotent di semua environment:
```python
# account/migrations/0001_assign_admin_group.py
def assign(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    admin, _ = Group.objects.get_or_create(name="ADMIN")
    perms = Permission.objects.filter(
        content_type__app_label__in=["student", "teacher", "account"]
    )
    admin.permissions.add(*perms)

def unassign(apps, schema_editor):
    Group = apps.get_model("auth", "Group").objects.filter(name="ADMIN").first()
    if admin:
        admin.permissions.clear()

class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(assign, unassign)]
```
Lalu jalankan `manage.py migrate`.

---

## MEDIUM

### 10. `MAILERS` — salah nama, bukan setting Django

**Masalah**
`managemant_school/settings.py:182-186` mendefinisikan `MAILERS`.
Django **tidak mengenal** setting ini; yang benar adalah `EMAIL_BACKEND`.

**Penyebab**
Salah ketik `EMAIL` → `MAIL`. Tidak ada error karena Django mengabaikan key yang
tidak dikenal.

**Dampak**
Konfigurasi email backend **tidak pernah terpasang**. Django memakai default
(`smtp` ke `localhost:25`). Saat fitur verifikasi akun/OTP ditambahkan, email akan
gagal terkirim atauemn berubah jadi exception `SMTPException` saat runtime.

**Solusi**
```python
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@sekolah.sch.id")
```

---

### 11. `fields` duplikat di `StudentOutputSerializer` — `nik` tidak pernah dikirim

**Masalah**
`student/serializer/serializer_output/student_output_serializer.py:8`:
```python
fields = ["id", "fullname", "nis", "nis", "nisn", "gender", "status", "is_active"]
#                      ^^^^^^        ^^^^^^  duplikat
```

**Penyebab**
`"nik"` salah ketik jadi `"nis"` (huruf `k` hilang), sementara entri `nis` asli tetap
ada.

**Dampak**
DRF **tidak** melempar error; dia diam-diam menimpa key yang sama. Verifikasi:
```
StudentOutput fields: ['id', 'fullname', 'nis', 'nisn', 'gender', 'status', 'is_active']
```
Artinya di dalam `student-profile`, field NIK siswa tidak pernah ada di response
padahal NIK adalah identitas utama siswa. Ini termasuk bug yang paling sunyi —
paling susah dideteksi karena tidak ada error sama sekali.

**Solusi**
```python
class Meta:
    model = Student
    fields = ["id", "fullname", "nik", "nis", "nisn", "gender", "status", "is_active"]
```

---

### 12. `SPECTACULAR_SETTINGS` tidak ada; `schema.yaml` hasil generate yang diedit manual

**Masalah**
`settings.py` tidak punya `SPECTACULAR_SETTINGS`. `schema.yaml` di root berisi
`title: SMK Kharya Bhakti API` / `version: 1.0.0` / `description: ...`, padahal
drf-spectacular tidak bisa menghasilkan itu tanpa konfigurasi.

**Penyebab**
`schema.yaml` dibuat once lalu **diedit tangan**. Perintah
`manage.py spectacular --file schema.yaml` (atau `python manage.py spectacular`)
akan menimpa dan menghapus blok `info`.

**Dampak**
```
$ python manage.py spectacular --validate
Warning: enum naming encountered a non-optimally resolvable collision for fields
named "status". ... resolved with "Status854Enum".
Warnings: 1  Errors: 0

$ spectacular --file ... # hasil generate:
info: {title: '', version: '0.0.0'}       <-- judul API kosong di Swagger UI
```
Dampak nyata: judul/version di Swagger UI kosong; setiap kali developer
regenerate schema, metadata produk hilang; nama enum `Status854Enum` muncul di
dokumentasi (artinya `ENUM_NAME_OVERRIDES` belum diisi). `schema.yaml` juga bisa
menjadi drift — dokumentasi tidak lagi mencerminkan kode.

**Solusi**
```python
SPECTACULAR_SETTINGS = {
    "TITLE": "SMK Kharya Bhakti API",
    "DESCRIPTION": "API untuk Management Sekolah",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "StudentStatusEnum": "student.models.Student.StatusChoice",
        "TeacherStatusEnum": "teacher.models.Teacher.StatusChoice",
        "GenderEnum": "student.models.Student.GenderChoice",
    },
    "TAGS": [{"name": "Auth"}, {"name": "student"}, {"name": "teacher"}],
}
```
Hapus `schema.yaml` dari repo, generate ke `.gitignore`/folder `docs/` saat build
(CI), atau jadikan output `/api/schema/` sebagai satu-satunya sumber kebenaran
(Swagger UI sudah membacanya langsung).

---

### 13. Register: password validator Django diabaikan, email tidak dinormalisasi

**Masalah**
`account/serializer/register_serializer.py:9-12`
```python
def validate_password(self, pw):
    if len(pw) < 8:
        raise sz.ValidationError("Minimal Password 8 Character")
    return pw
```
`services.py:145` sudah mengkonfigurasi 4 `AUTH_PASSWORD_VALIDATORS`, tapi tidak
satu pun dipakai. `validate_email` (`:19-22`) membandingkan email mentah.

**Penyebab**
Validasi dibuat manual sepanjang RequiredLengthValidator saja.

**Dampak**
- `AUTH_PASSWORD_VALIDATORS` = kode mati. `UserAttributeSimilarityValidator`,
  `CommonPasswordValidator`, `NumericPasswordValidator` tidak pernah jalan.
- Password lemah diterima: `password12345`, `qwerty123`, `11111111`, atau `admin`
  + nama sendiri lolos.
- Email bersifat case-sensitive di query: `Budi@Mail.com` dan `budi@mail.com`
  lolos sebagai dua akun berbeda, padahal secara bisnis satu orang._email
  database jadi berantakan.

**Solusi**
```python
from django.contrib.auth import password_validation

def validate_password(self, value):
    password_validation.validate_password(value)   # pakai 4 validator dari settings
    return value

def validate_email(self, value):
    value = value.strip().lower()
    if User.objects.filter(email__iexact=value).exists():
        raise sz.ValidationError("Email sudah terdaftar.")
    return value

def validate_username(self, value):
    value = value.strip()
    if User.objects.filter(username__iexact=value).exists():
        raise sz.ValidationError("Username tidak tersedia.")
    return value
```

---

### 14. User hasil register tidak dapat_group/permission apa pun

**Masalah**
`account/views/register_viewset.py:70` hanya `serializer.save()`. Tidak ada
penugasan group.

**Penyebab**
Belum ada keputusan bisnis: group mana yang diberikan ke user baru.

**Dampak**
User yang berhasil register **langsung 403 di seluruh endpoint**. Reproduksi:
`LOGIN: 200 {"message":"Berhasil Login","user_role":[],"user_id":8,...}` → request
berikutnya `GET /student/... -> 403`. Ini pengalaman pengguna yang buruk (register sukses tapi tidak
bisa dipakai) dan mudah disalahartikan sebagai bug auth. Kondisi DB saat ini
membuktikan: `eko` dan `riski2` tidak punya group.

**Solusi**
Tergantung kebutuhan, pilih salah satu:
```python
def create(self, validated_data):
    user = super().create(validated_data)
    user.is_active = False          # opsional: tunggu verifikasi email dulu
    user.save(update_fields=["is_active"])
    default_group, _ = Group.objects.get_or_create(name="STAFF")
    user.groups.add(default_group)  # grup default dengan permission minimum
    return user
```
Grup default **wajib** punya permission minimum (mis. `view_` saja) supaya user
baru bisa melihat data tetapi tidak bisa menghapus.

---

### 15. Migration `teacher/0003` memakai default di luar `choices`

**Masalah**
`teacher/migrations/0003_teacher_status.py:16`:
```python
field=models.CharField(choices=[('active','Active'),('transfer','Transfer'),('cut off','Cut Off')],
                        default='Active', max_length=80),
```
Nilai default `'Active'` (kapital) **tidak ada** di `choices` (nilainya `'active'`).

**Penyebab**
Yang ditulis adalah *label* choice, bukan *value*-nya.

**Dampak**
Baris yang dibuat oleh migration itu mendapat `status = 'Active'`, nilai yang tidak
valid menurut `Teacher.StatusChoice.values == ['active','transfer','cut off']`.
Konsekuensi: `full_clean()` akan menolak, `TeacherStatusEnum` di OpenAPI tidak
mencakup `'Active'`, dan serialisasi response menghasilkan nilai di luar enum —
frontend yang memvalidasi enum akan gagal parse. Saat ini data sudah bersih
(`invalid status rows: 0`), jadi baru bom waktu, tapi tidak akan pernah self-heal
untuk baris yang terlanjur tersimpan.

**Solusi**
Perbaiki migration tersebut (bila belum dipakai di environment lain) dan tambahkan
data migration untuk membersihkan:
```python
migrations.RunSQL(
    sql='UPDATE teacher_teacher SET status = %s WHERE status = %s;',
    params=['active', 'Active'],
    reverse_sql=migrations.RunSQL.noop,
),
```
Semua model yang punya `choices` sebaiknya `null=False` + `default=<value valid>`
atau `null=True` tanpa default, supaya data mustahil menyalahi enum.

---

### 16. Tidak ada pagination pada endpoint list, plus `print()` di dalam `list()`

**Masalah**
`student/views/student_viewset.py:14-22` dan `teacher/views/teacher_viewset.py:10-11`
— semua `get_queryset()` mengembalikan queryset penuh tanpa pagination, dan
`StudentViewSet.list` override berisi `print()` debug.

**Penyebab**
`REST_FRAMEWORK` tidak punya `DEFAULT_PAGINATION_CLASS`; `list()` masih contain
kode debug saat dred quickly.

**Dampak**
- `GET /student/school/api/student/` mengembalikan **seluruh** tabel dalam satu
  response. Ribuan siswa = response berukuran besar, latency tinggi, memory spike,
  dan menjadi denial-of-service ringan dari sisi client.
- `print("SESSION:", request.session.session_key)` berjalan di setiap request list,
  membocorkan session key ke stdout/log.

**Solusi**
```python
REST_FRAMEWORK = {
    ...,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}
```
Hapus override `list()` di `StudentViewSet` seluruhnya.

---

### 17. `related_name='teacher'` membuat aksesori ambigu

**Masalah**
`teacher/models/teacher_profile_model.py:5`
```python
teacher = md.OneToOneField(Teacher, on_delete=md.PROTECT, related_name='teacher')
```

**Penyebab**
Default `related_name` seharusnya `teacherprofile`; di-override menjadi `teacher`,
sama dengan nama field forward.

**Dampak**
Reverse accessor menjadi `teacher.teacher` — dari `Teacher` kita bisa mengambil
profilnya lewat `.teacher`, sementara dari `TeacherProfile` juga via `.teacher`.
Keduanya valid, tapi sangat membingungkan dan rawan bug di kode berikutnya.
`manage.py check` **tidak** menandai ini (0 issue), jadi tidak akan ketahuan otomatis.

**Solusi**
```python
teacher = models.OneToOneField(Teacher, on_delete=models.PROTECT, related_name="profile")
```
Akses: `teacher.profile`. Ini juga konsisten dengan `StudentProfile` yang memakai
default (reverse `student.studentprofile`).

---

## LOW

### 18. `email` pada profile tidak unik

**Masalah**
`student/models/studentProfile_model.py:6` dan `teacher/models/teacher_profile_model.py:6`
menggunakan `md.EmailField()` tanpa `unique=True`.

**Dampak**
Dua siswa bisa memakai email yang sama → sulit untuksignup/reset password, dan
"cari siswa berdasarkan email" jadi ambigu.

**Solusi**
```python
email = models.EmailField(unique=True)
```
Lalu jalankan dulu pendeteksian duplikat di DB sebelum membuat migration unique
constraint.

---

### 19. `print()` debug membocorkan session key ke log server

**Masalah**
`core/permission/student_view_permission.py:6-20` (8 baris `print` pada **setiap**
request ke endpoint mana pun), `account/views/login_viewset.py:64-66`,
`student/views/student_viewset.py:16-18`.

**Dampak**
`request.session.session_key` tertulis di stdout/log pada setiap request. Session key
adalah kredensial — siapa pun yang bisa membaca log (log aggregator, terminal
shared, CI output) bisa meniru cookie session dan menyamar sebagai user tersebut.
`username` juga ikut tercetak. Terus-menerus, bukan hanya saat debugging.

**Solusi**
Hapus seluruh `print()`. Bila perlu log terstruktur, pakai `logging` dengan level
`DEBUG` yang nonaktif di produksi:
```python
logger = logging.getLogger(__name__)
logger.debug("permission check user=%s method=%s", request.user, request.method)
```

---

### 20. `if not user.is_active` adalah dead code

**Masalah**
`account/serializer/login_serializer.py:18-19` memeriksa `user.is_active` setelah
`authenticate()`.

**Penyebab**
`ModelBackend.authenticate()` sudah memanggil `user_can_authenticate()` yang
menolak user tidak aktif, jadi `authenticate()` sudah mengembalikan `None` lebih dulu.

**Dampak**
Branch `"Informasi Akun Tidak Di Temukan"` (yang didokumentasikan di `schema.yaml:64`
dan `login_viewset.py:49-54`) tidak pernah tercapai. User nonaktif selalu mendapat
pesan `"Username Ata Password Salah"`. Konsekuensinya, dokumentasi API =
menyesatkan.

**Solusi**
Hapus blok tersebut, atau ubah jadi satu pesan error tunggal (jangan bocorkan
apakah username itu ada). Contoh pesan sama untuk user tidak ada maupun password
salah: `"Username atau password salah."`

---

### 21. Struktur paket tidak lengkap dan `academic` tidak terdaftar

**Masalah**
- `academic/` **tidak ada** di `INSTALLED_APPS` (`settings.py:36-51`) padahal
  `academic/apps.py` sudah ada (`AcademicConfig`).
- Tidak ada `__init__.py` di: `academic/models/`, `academic/views/`,
  `academic/serializer/`, `core/services/`, `core/services/student/`.
- `docs/` kosong.
- Nol test di seluruh app (`student/tests.py`, `teacher/tests.py`, `account/tests.py`,
  `academic/tests.py` semuanya hanya "# Create your tests here.").

**Penyebab**
App `academic` masih hasil `startapp` tapi belum dikerjakan.

**Dampak**
- Model yang nanti dibuat di `academic/models` **tidak akan pernah dimuat** —
  tidak ada error, tidak adaigrations, tabel tidak pernah dibuat. Ini bug yang
  sangat mahal dideteksi belakangan.
- Tidak ada `__init__.py` → paket bukan "regular package"; sekarang masih jalan
  karena PEP 420 namespace package, tapi tooling (pytest, sebagian IDE, freeze) bisa
  gagal mengimpornya.
- Tanpa test, semua bug di dokumen ini (terutama #2, #3, #5) akan mudah berulang.

**Solusi**
```python
INSTALLED_APPS = [..., 'account', 'student', 'teacher', 'academic']
```
Buat `__init__.py` kosong di semua direktori paket di atas, lalu `manage.py makemigrations`.
Tambahkan test minimal untuk setiap temuan CRITICAL/HIGH di atas — semuanya sudah
terbukti reproducible, jadi jadi test regression yang murah.

---

### 22. Kebersihan kode

**Masalah**
- `student/views/student_viewset.py:3-5`: `extend_schema`, `OpenApiExample`,
  `inline_serializer`, `sz`, `IsAuthenticated` di-import tapi tidak dipakai.
- `managemant_school/settings.py:16`: `from datetime import timedelta` tidak dipakai.
- `core/services/student/student_services.py:5-11`: parameter `intances` (typo dari
  `instance`); `update_student()` hanya berisi `pass` — tidak melakukan apa-apa;
  `.get(pk=...)` tidak menangani `DoesNotExist`; dan seluruh service ini tidak
  dipanggil dari mana pun.
- `student/views/student_viewset.py:22`: `order_by("-fullname")` → daftar student
  terurut Z→A. Sudah pasti disengaja atau salah?
- `settings.py:164`: `LANGUAGE_CODE = 'en-us'` sementara UI & dokumentasi Bahasa
  Indonesia.

**Dampak**
Sedikit, tapi menambah noise saat code review dan membingungkan pembaca kode
(ejaan `intances` + method kosong membuat pembaca mengira ada logika
bisnis tersembunyi di sana).

**Solusi**
Hapus import tak terpakai. Untuk service: selesaikan atau hapus
`core/services/student/student_services.py` sampai benar-benar dipakai — jangan
biarkan file setengah jadi yang tidak punya implementasi. Pastikan `order_by`
sesuairequirement dan `LANGUAGE_CODE = 'id'` bila UI berbahasa Indonesia.

---

## Urutan pengerjaan yang disarankan

**Tahap 1 — hentikan kerusakan data & akses (hari 1)**
1. Bug #2 — `nis` unique/blank (500 + data integrity)->Selesai
2. Bug #3 — validasi OneToOne (500 + pencurian profil)-Selesai
3. Bug #1 — `ALLOWED_HOSTS` (seluruh API tidak bisa diakses) -> di sesuiakan
4. Bug #4 — rotasi `SECRET_KEY` + password DB, tambahkan `.gitignore` ->Selesai

**Tahap 2 — amankan auth (hari 2)**
5. Bug #5 — `context.get("request")`
6. Bug #8 — throttle + endpoint logout
7. Bug #6 — permission bypass `OPTIONS`/`HEAD`
8. Bug #7 — `DEBUG`/secure cookie dari env
9. Bug #13, #14 — register: password validator + group default

**Tahap 3 — konsistensi data & konfigurasi (hari 3)**
10. Bug #9 — permission `studentprofile` untuk group `ADMIN`
11. Bug #11 — duplikat `"nis"` di `StudentOutputSerializer`
12. Bug #15 — default status di luar `choices`
13. Bug #17, #18 — `related_name`, email unik
14. Bug #10, #12 — `EMAIL_BACKEND`, `SPECTACULAR_SETTINGS`

**Tahap 4 — kualitas (berikutnya)**
15. Bug #16 — pagination + hapus `print()`
16. Bug #19, #20 — hapus `print()`, rapikan pesan login
17. Bug #21 — daftarkan `academic`, lengkapi paket, tulis test
18. Bug #22 — bersihkan kode

---

## Catatan verifikasi

- `python manage.py check` → **System check identified no issues (0 silenced)**.
  Artinya tak satu pun bug di atas terdeteksi oleh check bawaan Django — semuanya
  butuh reproduksi manual.
- `python manage.py makemigrations --check --dry-run` → **No changes detected**.
  Model dan migration file sudah sinkron.
- Semua reproduksi dilakukan di dalam `transaction.atomic()` + `set_rollback(True)`.
  Data sebelum dan sesudah audit sudah diverifikasi identik:
  `Student: 5, StudentProfile: 1, Teacher: 1, TeacherProfile: 1, User: eko/riski/riski2`.
- Tidak ada file kode yang diubah dalam proses audit ini.
