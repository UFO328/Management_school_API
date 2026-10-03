# Laporan Testing API Teacher

**Tanggal test:** 2026-10-03
**Lingkup:** app `teacher` saja (endpoint `/teacher/school/api/...`) — tanpa mengubah file apapun
**Metode:** DRF `APIClient` (force_authenticate) dengan user tester yang diberi semua permission `teacher.*`
**Hasil:** 30 kasus test — **27 sesuai ekspektasi, 3 perilaku berbeda dari ekspektasi awal (bukan bug, dijelaskan di bagian Temuan)**

---

## 1. Konfigurasi API

| Item | Nilai |
|---|---|
| Prefix URL | `/teacher/school/api/` |
| Endpoint | `/teacher/` dan `/teacher-profile/` (ModelViewSet: LIST, CREATE, RETRIEVE, UPDATE, PARTIAL_UPDATE, DESTROY) |
| Autentikasi | `SessionAuthentication` |
| Permission | `SchoolModelPermissions` (turunan `DjangoModelPermissions`) — butuh user login + permission `teacher.view/add/change/delete_teacher` & `..._teacherprofile` |
| Pagination | `PageNumberPagination`, `page_size = 20` |
| Database | PostgreSQL |

**Data awal saat test:** 1 teacher (`Andi Wijaya`, nik `3201011501900002`, status `active`) + 1 teacher-profile (email `andi@gmail.com`).

---

## 2. Endpoint `/teacher/` (TeacherViewSet)

| # | Method | Kasus | Ekspektasi | Nyata | Status |
|---|---|---|---|---|---|
| 1 | GET | list tanpa autentikasi | 401 | **403** `{"detail":"Authentication credentials were not provided."}` | ⚠️ lihat Temuan A |
| 2 | GET | list user tanpa permission teacher | 403 | 403 `{"detail":"You do not have permission to perform this action."}` | ✅ |
| 3 | GET | list (dengan permission) | 200 | 200, format paginasi `{count, next, previous, results}` | ✅ |
| 4 | GET | detail teacher id=1 | 200 | 200 (id, fullname, nik, status, is_active, created_at, updated_at) | ✅ |
| 5 | GET | detail id=999999 | 404 | 404 `{"detail":"No Teacher matches the given query."}` | ✅ |
| 6 | POST | payload valid | 201 | 201, teacher baru terbentuk | ✅ |
| 7 | POST | tanpa `fullname` | 400 | 400 `{"fullname":["This field is required."]}` | ✅ |
| 8 | POST | tanpa `nik` | 400 | 400 `{"nik":["This field is required."]}` | ✅ |
| 9 | POST | `nik` duplikat | 400 | 400 `{"nik":["teacher with this nik already exists."]}` | ✅ |
| 10 | POST | `status` = "nonactive" | 400 | 400 `{"status":["\"nonactive\" is not a valid choice."]}` | ✅ |
| 11 | PUT | update penuh (status → transfer) | 200 | 200 | ✅ |
| 12 | PUT | tanpa `nik` | 400 | 400 `{"nik":["This field is required."]}` | ✅ |
| 13 | PATCH | update sebagian (fullname) | 200 | 200 | ✅ |
| 14 | PATCH | `status` = "bogus" | 400 | 400 `{"status":["\"bogus\" is not a valid choice."]}` | ✅ |
| 15 | DELETE | teacher yang punya profile | 400 | 400 `{"detail":"User Ini masih Memiliki Profile"}` | ✅ |
| 16 | DELETE | teacher tanpa profile | 204 | 204 (tanpa body) | ✅ |
| 17 | OPTIONS | metadata | 200 | 200 (skema field: fullname max 255, nik max 30, status choices active/transfer/cut off, is_active default true) | ✅ |

## 3. Endpoint `/teacher-profile/` (TeacherProfileViewSet)

| # | Method | Kasus | Ekspektasi | Nyata | Status |
|---|---|---|---|---|---|
| 18 | GET | list | 200 | 200, field `teacher` nested `{id, fullname}` | ✅ |
| 19 | GET | detail id=1 | 200 | 200 (teacher nested + email, phone, address) | ✅ |
| 20 | GET | detail id=999999 | 404 | 404 `{"detail":"No TeacherProfile matches the given query."}` | ✅ |
| 21 | POST | valid pakai `teacher_id` | 201 | 201 (`teacher_id` write-only, response pakai `teacher` nested) | ✅ |
| 22 | POST | `teacher_id` = 999999 | 400 | 400 `{"teacher_id":["Invalid pk \"999999\" - object does not exist."]}` | ✅ |
| 23 | POST | profile kedua untuk teacher sama | 400 | 400 `{"teacher_id":["teacher ini sudah memiliki profil."]}` | ✅ |
| 24 | POST | email tidak valid | 400 | 400 `{"email":["Enter a valid email address."]}` | ✅ |
| 25 | POST | phone 14 karakter (>13) | 400 | 400 `{"phone":["Ensure this field has no more than 13 characters."]}` | ✅ |
| 26 | POST | tanpa `address` | 400 | **201** dengan `address: ""` | ⚠️ lihat Temuan B |
| 27 | PATCH | update sebagian (email) | 200 | 200 | ✅ |
| 28 | PUT | update penuh | 200 | 200 | ✅ |
| 29 | DELETE | hapus profile | 204 | 204 | ✅ |
| 30 | GET | list tanpa autentikasi | 401 | **403** `{"detail":"Authentication credentials were not provided."}` | ⚠️ lihat Temuan A |

---

## 4. Temuan

**A. Request tanpa autentikasi mengembalikan 403, bukan 401**
`SessionAuthentication` tidak melempar 401 saat header kredensial tidak ada; request diteruskan sebagai `AnonymousUser` lalu ditolak oleh `SchoolModelPermissions` → DRF mengembalikan 403 `Authentication credentials were not provided.` Perilaku ini konsisten di kedua endpoint. Secara REST konvensi 401 lebih lazim untuk "belum login", tetapi fungsionalitas tetap aman (tidak ada data bocor).

**B. Field `address` bersifat opsional**
Model `TeacherProfile.address` punya `blank=True`, sehingga serializer menjadikannya tidak wajib. POST tanpa `address` → 201 dengan nilai `""`. Ini sesuai desain model, bukan bug.

**C. Peringatan `UnorderedObjectListWarning`**
QuerySet `Teacher` dan `TeacherProfile` tidak punya `Meta.ordering`, sehingga hasil pagination bisa tidak konsisten antar halaman. Rekomendasi: tambahkan `ordering` di `Meta` model (misal `["-id"]`). *(Catatan untuk developer — perubahan ini tidak saya lakukan karena instruksi tidak mengedit file.)*

## 5. Kesimpulan

API teacher berfungsi dengan baik: CRUD lengkap, validasi field (required, unique nik, choice status, email, max_length phone), proteksi delete via `ProtectedError` (pesan: *"User Ini masih Memiliki Profile"*), aturan 1 teacher = 1 profile, pembatasan permission per metode HTTP, dan pagination semuanya bekerja sesuai desain. Tidak ditemukan bug; 3 penyimpangan dari ekspektasi awal telah dijelaskan di atas.

*Catatan: semua data test sudah dibersihkan setelah testing — database kembali ke kondisi awal (1 teacher, 1 profile).*
