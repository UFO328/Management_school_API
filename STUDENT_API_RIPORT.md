# LAPORAN TESTING API STUDENT (app `student`) — Ronde 2

- **Tanggal:** 2026-10-03
- **Base URL:** `http://127.0.0.1:8000/student/school/api` (diuji lewat Django test client, bukan server live)
- **Endpoint yang diuji (DAN TIDAK LEBIH — sesuai instruksi):**
  - `/student/school/api/student/` → list, create, retrieve, update (PUT), partial_update (PATCH), destroy (DELETE), OPTIONS, HEAD
  - `/student/school/api/student-profile/` → list, create, retrieve, update (PUT), partial_update (PATCH), destroy (DELETE)
- **API lain (auth, teacher, schema/docs) TIDAK diuji** sesuai instruksi.
- **Cara test:** 75 test otomatis dengan `django.test.Client(enforce_csrf_checks=True)` — CSRF ditegakkan secara nyata — terhadap **database test terpisah** (`test_managemant_school`, dibuat & dihapus otomatis oleh test runner). Database dev **tidak disentuh** (verifikasi: row count sebelum & sesudah = 5). Autentikasi session test dibuat via Django ORM (`force_login`), **bukan** via API `/auth/` — sehingga hasil testing student API independen dari kondisi API auth.
- **File yang diubah:** **TIDAK ADA.** Harness berada di luar repo (`/data/data/com.termux/files/usr/tmp/opencode/studenttest/`). `git status` sebelum dan sesudah testing **identik**. Satu-satunya perubahan di repo adalah laporan ini (file sudah ada, isi diperbarui).

## Ringkasan Eksekutif

| Seksi | Test | PASS | FAIL |
|---|---:|---:|---:|
| A. Authorization / RBAC | 15 | 15 | 0 |
| B. Student list & read | 12 | 12 | 0 |
| C. Student create (+CSRF, form, validasi) | 18 | 18 | 0 |
| D. Student update | 6 | 6 | 0 |
| E. Student delete | 4 | 4 | 0 |
| F. Student profile | 20 | 20 | 0 |
| **TOTAL** | **75** | **75** | **0** |

**Pass rate: 100 %.** Tidak ada HTTP 500, tidak ada crash, tidak ada kebocoran data, tidak ada data yang berubah/tersimpan dari request tanpa CSRF.

### Verdict
> API student & student-profile **lulus semua 75 test**. Keempat bug yang ditemukan di ronde testing sebelumnya (pagi ini, lihat catatan di bawah) **semuanya sudah diperbaiki dan terverifikasi lewat request nyata**. CRUD, validasi, RBAC, CSRF, protected delete, pagination, one-to-one integrity semuanya bekerja dengan benar.

## Perbandingan dengan ronde sebelumnya (status bug lama)

Ronde sebelumnya (file ini versi lama, 68 test: 61 PASS / 7 FAIL) melaporkan 4 bug. Ronde ini menguji ulang keempatnya secara spesifik:

| Bug lama | Deskripsi | Status sekarang | Bukti test |
|---|---|---|---|
| BUG-1 (P2) | Student dibuat `is_active=False` saat POST form-urlencoded tanpa field `is_active` | ✅ **FIXED** | C2, C3 |
| BUG-2 (P1) | Response `student-profile` tidak pernah menyertakan `id` (client-blocking) | ✅ **FIXED** | F1, F2, F3 |
| BUG-3 (P3) | `OPTIONS`/`HEAD /student/` → `200` untuk user tanpa permission (bypass RBAC) | ✅ **FIXED** | A5, A6 |
| BUG-4 (P3) | Queryset `student-profile` tanpa `order_by()` → `UnorderedObjectListWarning` (paginasi tidak stabil) | ✅ **FIXED** | F12 |

**Detail verifikasi fix:**

- **BUG-1 FIXED** — `StudentSerializer` kini mendeklarasikan `is_active = sz.BooleanField(default=True)`. Repro kasus lama:
  ```
  POST /student/school/api/student/
  Content-Type: application/x-www-form-urlencoded
  fullname=FormUser&nik=...&nisn=...&gender=pria&status=active   (tanpa is_active)
  ```
  → `201` dan row di DB: `is_active = True` ✅ (sebelumnya `False`). Response aktual:
  ```json
  {"id":1,"is_active":true,"fullname":"Form User","nik":"4000000002","nis":null,"nisn":"4000000002","gender":"pria","status":"active","created_at":"...","updated_at":"..."}
  ```
- **BUG-2 FIXED** — `StudentProfileSerializer.fields` kini menyertakan `"id"`. Response create (`201`) kini:
  ```json
  {"id":1,"student":{"id":2,"fullname":"Profile Owner","nis":null,"nik":"4000000050","nisn":"4000000050","gender":"pria","status":"active","is_active":true},"email":"...","phone":"...","birth_date":"...","birth_place":"...","address":"..."}
  ```
  Frontend kini bisa melakukan PATCH/DELETE terhadap profile. **Bonus:** nested `student` juga sudah benar — field `nik` muncul (sebelumnya ada duplikasi key `nis` di `StudentOutputSerializer`, kini `"nis","nik"`).
- **BUG-3 FIXED** — `SchoolModelPermissions.get_required_permissions()` kini memetakan `OPTIONS`/`HEAD` ke permission `view_*`. User tanpa permission: `OPTIONS → 403`, `HEAD → 403`, `GET → 403` (sebelumnya OPTIONS/HEAD → 200). User dengan `view_student`: `OPTIONS → 200` (A15).
- **BUG-4 FIXED** — `StudentProfileViewSet.get_queryset()` kini `.select_related("student").order_by("-id")`. `GET /student-profile/` **tidak** lagi menghasilkan `UnorderedObjectListWarning` (F12, ditangkap via `warnings.catch_warnings`).

**Perbaikan lain yang terverifikasi di ronde ini (di luar 4 bug lama):**
- `perform_destroy()` kini menangkap `ProtectedError` → `400 {"detail":"User Ini masih Memiliki Profile"}` yang friendly, bukan error 500 (E2). Response aktual persis seperti itu.
- Ordering `StudentViewSet` kini `order_by("fullname")` ASC dan konsisten di semua halaman (B3, B5).
- `settings.py`: `DEBUG` dari env, `ALLOWED_HOSTS`, pagination default (`PAGE_SIZE: 20`), cookie secure mengikuti `DEBUG` — semuanya berperilaku benar dalam pengujian.

## Yang BERFUNGSI BAIK (75 test PASS)

| Area | Bukti |
|---|---|
| **Authorization / RBAC** | Anonim → `403` (A1, A2, A3, A18); user tanpa permission → `403` untuk GET/OPTIONS/HEAD/POST/PUT/PATCH/DELETE (A4–A12); user dengan `view_*` → `200` GET & `200` OPTIONS (A13, A15); RBAC terisolasi per-method: viewer tidak bisa POST (A14) |
| **List & read** | Envelope paginasi `{count,next,previous,results}` (B1); semua 10 field model terekspos (B2); ordering ASC `fullname` (B3); paginasi 26 data → page1=20, page2=6 (B4, B5); `?page=999`/`?page=abc` → `404` (B6, B7); `?page_size=1000` di-clamp ke 20 (B8); retrieve valid/`404`/non-numerik `404` (B9–B11); format suffix `.json` → `200` (B12) |
| **Validasi create** | 13 kasus: missing fullname/nik/nisn/gender/status (C4–C8), choice invalid gender/status (C9, C10), max_length fullname 256 & nik 31 (C11, C12), empty string (C13), duplikat nik/nisn/nis → `400` pada field yang tepat (C14–C16), 2× `nis=NULL` diperbolehkan (C17) |
| **CSRF** | POST/PATCH/DELETE tanpa `X-CSRFToken` → `403` **dan data tidak berubah/tersimpan** (C18, D5, E4, F17) |
| **Update** | PUT lengkap → `200` (D1); PUT kurang field → `400` (D2); PATCH partial hanya mengubah field dikirim (D3); PATCH menabrak NIK lain → `400` **bukan 500** (D4); PATCH id tak ada → `404` (D6) |
| **Delete** | DELETE tanpa profile → `204` & row terhapus (E1); **protected delete**: student ber-profile → `400 {"detail":"User Ini masih Memiliki Profile"}` & row aman (E2); id tak ada → `404` (E3) |
| **Student profile** | Create valid → `201` + response **punya `id`** + nested student lengkap (F1, F3, F4); list & retrieve punya `id` (F2, F3); `student_id` write_only (F5); one-to-one dijaga: profile ke-2 untuk student sama → `400 "sudah memiliki profil"` (F6); `student_id` tak dikenal → `400` bukan `500` (F7); validasi email/phone/address (F8–F11); boundary phone 14 char → `201` (F10); paginasi stabil tanpa peringatan (F12); PATCH tersimpan ke DB (F13); re-assign ke student sendiri → `200` (F14); re-assign ke student ber-profile lain → `400` (F15); DELETE → `204` (F16); PUT lengkap → `200`, PUT kurang → `400` (F19, F20) |

## Catatan metodologi

- **Hanya API student yang diuji** sesuai instruksi. Endpoint `/auth/school/api/*`, `/teacher/school/api/*`, `/api/schema/`, `/api/docs/`, `/api/redoc/` **tidak disentuh** dalam ronde ini.
- Session test dibuat via ORM (bukan API login), jadi temuan di atas **independen** dari kondisi API auth.
- Semua klaim di atas direproduksi dengan request HTTP nyata terhadap test database; bukan analisis statis.
- Data uji (user `admin`/`viewer`/`editor`/`noperm`, 26+ student, profile) hidup & mati bersama database test — **tidak ada sisa data** di database dev (diverifikasi: 5 row sebelum = 5 row sesudah).
- Harness bisa di-run ulang kapan saja:
  ```bash
  python3 /data/data/com.termux/files/usr/tmp/opencode/studenttest/run_student_tests.py
  ```
  (hasil mentah ditulis ke `results.json` di direktori yang sama)

## Sisa catatan kecil (bukan kegagalan)

| # | Catatan | Dampak |
|---|---|---|
| N1 | Response `student-profile` tetap tidak menyertakan `created_at`/`updated_at` (field list eksplisit di serializer). | Rendah — informasi opsional; client bisa menampilkan jika diinginkan dengan menambah field. |
| N2 | `PAGE_SIZE` request param (`?page_size=...`) diabaikan (selalu 20). | Justru **baik** untuk keamanan (anti DoS memory); perilaku yang diharapkan. |

## Rekomendasi prioritas

Tidak ada bug yang tersisa pada API student. Untuk menjaga kualitas:
1. Pertahankan `is_active = sz.BooleanField(default=True)` eksplisit di `StudentSerializer` (jangan hapus — kunci fix BUG-1).
2. Jika ingin konsistensi penuh antar-modul, pertimbangkan mengekspos `created_at`/`updated_at` di `StudentProfileSerializer` (opsional).
3. Rekomendasi dari audit lintas-app (`report_api.md`) yang **di luar cakupan ronde ini** masih menunggu verifikasi ulang di app `account` dan `teacher` — tidak diuji di sini sesuai instruksi.
