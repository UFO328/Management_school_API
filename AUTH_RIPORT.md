# LAPORAN TESTING API AUTH (app `account`)

- **Tanggal:** 2026-10-03
- **Base URL:** `http://127.0.0.1:8000/auth/school/api` (diuji lewat Django test client, bukan server live)
- **Endpoint yang diuji (DAN TIDAK LEBIH — sesuai instruksi):**
  - `POST /auth/school/api/login/` (LoginAPIView)
  - `POST /auth/school/api/logout/` (LogoutAPIView)
  - `POST /auth/school/api/register/` (RegisterAPIView)
  - `GET /auth/school/api/csrf/` (csrf_view)
  - + metode lain (GET/HEAD/OPTIONS/PUT) ke keempat endpoint di atas untuk cek verb & routing
- **API lain (student, teacher, admin, schema/docs) TIDAK diuji** sesuai instruksi.
- **Cara test:** 55 test otomatis dengan `django.test.Client(enforce_csrf_checks=True)` — CSRF ditegakkan secara nyata — terhadap **database test terpisah** (`test_managemant_school`, dibuat & dihapus otomatis oleh test runner). Database dev **tidak disentuh** (verifikasi row count sebelum & sesudah identik: `auth_user=4`, `axes_accessattempt=0`, `django_session=1`, `axes_accesslog=41`). Harness berada di luar repo (`/data/data/com.termux/files/usr/tmp/opencode/authtest/auth_tests.py`). `git status` sebelum dan sesudah testing **identik** — **TIDAK ADA file repo yang diubah/diedit**.
- **Environment:** Python 3.14.6 · Django 6.1 · DRF 3.18.0 · django-axes 8.3.1 · PostgreSQL 127.0.0.1:5432 (user `u0_a422`) · DEBUG=True

## Ringkasan Eksekutif

| Seksi | Test | PASS | FAIL |
|---|---:|---:|---:|
| A. CSRF endpoint (`/csrf/`) | 3 | 3 | 0 |
| B. Register (`/register/`) | 22 | 20 | 2 |
| C. Login (`/login/`) | 12 | 12 | 0 |
| D. Axes lockout (brute-force) | 5 | 5 | 0 |
| E. Logout (`/logout/`) | 5 | 5 | 0 |
| F. Method / verb (GET/HEAD/OPTIONS/PUT) | 6 | 6 | 0 |
| G. Misc (trailing slash, email case) | 2 | 2 | 0 |
| **TOTAL** | **55** | **53** | **2** |

**Pass rate: 96.4 %.** Tidak ada HTTP 500, tidak ada crash, tidak ada kebocoran password/session.

### Verdict
> API auth **berfungsi dengan benar secara keseluruhan** (login, register, logout, CSRF, lockout brute-force django-axes semua bekerja sesuai desain). **2 test gagal sengaja dibiarkan gagal** karena keduanya adalah **bug nyata** (F-1, F-2): password yang sama dengan username diterima, dan username dengan format tidak valid (spasi) diterima. Keduanya terjadi karena serializer memanggil validasi password Django tanpa argumen `user` dan tidak memvalidasi format username. Ada juga 3 ketidaksesuaian dokumentasi (docstring/OpenAPI) yang perlu diperbaiki (F-3 s/d F-5).

## Temuan (Findings)

| ID | Severity | Deskripsi | Bukti test | Status |
|---|---|---|---|---|
| F-1 | **SEDANG (P2)** | Password **sama dengan username** diterima (`201`). `UserAttributeSimilarityValidator` mati karena `register_serializer.py:13` memanggil `validate_password(pw)` **tanpa argumen `user`** — validator similarity langsung `return` bila `user=None`. | B09 | 🔴 OPEN |
| F-2 | **RENDAH (P3)** | Username **format tidak valid** (mengandung spasi, `"bad user"`) diterima (`201`). Serializer hanya `CharField(max_length=150)` + cek panjang/unik; `create_user()` tidak menjalankan `full_clean()` sehingga `UnicodeUsernameValidator` Django dilewati. Dampak: user dengan username spasi bisa dibuat via API dan berpotensi mematahkan form admin saat edit user tsb. | B19 | 🔴 OPEN |
| F-3 | DOKUMENTASI | Docstring `LoginAPIView` mengklaim *"Dibatasi 10x per menit per IP (ScopedRateThrottle)"*, tapi **tidak ada** `throttle_classes` di view maupun `DEFAULT_THROTTLE_CLASSES` di `settings.py`. 12× login valid berturut-turut → semua `200`. Yang aktif hanya lockout django-axes (5× gagal). | C11 | 🔴 OPEN |
| F-4 | DOKUMENTASI | Contoh response 429 di OpenAPI (`login_viewset.py`) menulis `"Request was throttled. Expected available in 60 seconds."` (pesan DRF throttle), padahal respons asli django-axes: `{"detail": "Account locked: too many login attempts. Please try again later."}`. | D01, D02 | 🔴 OPEN |
| F-5 | DOKUMENTASI | Contoh error 400 di OpenAPI menyebut *"Akun Belum Verifkasi OTP"* / `"Informasi Akun Tidak Di Temukan"` — **tidak ada logika OTP** di mana pun dalam kode. | — | 🔴 OPEN |

### Saran perbaikan
- **F-1:** ubah `register_serializer.py` → `validate_password(pw, User(username=...))` (pass user agar similarity validator jalan), atau validasi manual `if pw == data["username"]`.
- **F-2:** tambahkan `UnicodeUsernameValidator` di `validate_username`, atau panggil `user.full_clean()` di `create()`.
- **F-3:** hapus klaim ScopedRateThrottle dari docstring, **atau** tambahkan benar `throttle_classes = [ScopedRateThrottle]` + `DEFAULT_THROTTLE_RATES` di settings.
- **F-4 / F-5:** perbarui `OpenApiExample` di `login_viewset.py` agar sesuai respons nyata.

## Observasi (bukan bug)

- **OBS-1 — Email uniqueness case-sensitive (G02):** `"Existing@Mail.com"` diterima (`201`) walau `"existing@mail.com"` sudah ada → 2 user dengan email "sama" beda huruf besar/kecil. Perilaku default Django/PostgreSQL; jika ingin case-insensitive perlu normalisasi email.
- **OBS-2 — CSRF token berputar setelah login (C12, E03, E04):** response `login` mengeluarkan `Set-Cookie: csrftoken` baru (karena `login()` melakukan `session.cycle_key()`). Token CSRF dari **sebelum** login sudah tidak valid (`403 CSRF Failed: ... incorrect.`). Frontend **wajib** memakai token terbaru (dari cookie response login atau panggil `/csrf/` lagi) saat POST logout. Ini perilaku Django yang benar.
- **OBS-3 — Register tanpa batas:** endpoint `/register/` tidak dilindungi throttle maupun axes → registrasi bot tanpa limit (design note).
- **OBS-4 — GET/OPTIONS `/logout/` → 403 (E05, F05):** DRF menjalankan permission check **sebelum** method routing, sehingga verb tidak valid pada endpoint proteksi tetap 403 (bukan 405) dan metadata OpenAPI tidak bocor ke anonim. Ini perilaku default DRF yang aman.
- **OBS-5 — POST `/csrf/` tanpa token → 403 (A02):** `csrf_view` adalah plain Django view (bukan DRF) sehingga `CsrfViewMiddleware` aktif penuh — unsafe method tanpa token ditolak. Dengan token valid → 200 (A03). Perilaku benar.

## Hal positif yang terverifikasi

- Login dengan password salah, user tidak ada, dan user tidak aktif → **pesan 400 yang sama** (`Username Atau Password Salah`) → tidak ada user enumeration (C03, C04, C08).
- Response login hanya berisi 4 field: `message`, `user_role`, `user_id`, `username` — **tidak ada password** (C01, C10).
- Register **tidak** menciptakan session (tanpa `sessionid` cookie) dan response hanya `{"message": ...}` (B17, B18).
- User baru **tanpa group** (`user_role: []`) — sesuai desain (penentuan group di admin) (B16, C01).
- `user_role` terisi benar dari group Django: `["admin","staff"]` (C02).
- django-axes bekerja: 5× gagal → **429** dengan pesan lockout yang benar, bahkan password **benar** pun tetap ditolak saat terkunci (D01, D02). Lockout ter-scope per **username+IP** (user lain tetap bisa login; IP lain tetap bisa login) (D03, D04). `AXES_RESET_ON_SUCCESS` bekerja (D05).
- CSRF: register/login (anonim) tidak perlu token; logout butuh session + token CSRF valid → `204`; tanpa token → `403 CSRF Failed: CSRF token missing.`; token salah → `403 ... incorrect.` (E01–E04, B20).
- Verb tidak diizinkan → `405` (F01, F02, F03, F06); URL tanpa trailing slash → `301` redirect (G01).
- Validasi password lengkap: too short, too common, entirely numeric → 400 (B06, B07, B08).

## Detail hasil test (respons aktual)

### A. CSRF endpoint
| Test | Skenario | Hasil |
|---|---|---|
| A01 | GET `/csrf/` | ✅ 200 `{"message": "CSRF cookie berhasil dibuat"}`, Set-Cookie `csrftoken` |
| A02 | POST `/csrf/` tanpa token | ✅ 403 (CsrfViewMiddleware aktif) |
| A03 | POST `/csrf/` dengan token valid | ✅ 200 |

### B. Register
| Test | Skenario | Hasil |
|---|---|---|
| B01 | Register valid (JSON) | ✅ 201 `{"message": "Akun Berhasil Di Buat"}`; user tersimpan, password ter-hash, `is_active=True` |
| B02 | Register valid (form-urlencoded) | ✅ 201 |
| B03 | Username duplikat | ✅ 400 `{"username": ["Username Tidak Tersedia"]}` |
| B04 | Email duplikat | ✅ 400 `{"email": ["Email Tidak Tersedia"]}` |
| B05 | Username < 7 char | ✅ 400 `{"username": ["Username Terlalu Pendek"]}` |
| B06 | Password 7 char | ✅ 400 `password: ["This password is too short...","This password is too common."]` |
| B07 | Password `"password"` | ✅ 400 `password: ["This password is too common."]` |
| B08 | Password `"12345678"` | ✅ 400 `password: ["This password is too common.","This password is entirely numeric."]` |
| **B09** | **Password == username (`simuser1`)** | 🔴 **201 — diterima!** (seharusnya 400). `validate_password(pw)` tanpa `user` → similarity validator mati |
| B10 | Email format salah | ✅ 400 `email: ["Enter a valid email address."]` |
| B11 | Body kosong | ✅ 400 ketiga field `This field is required.` |
| B12 | Tanpa password | ✅ 400 `password: ["This field is required."]` |
| B13 | Tanpa username | ✅ 400 `username: ["This field is required."]` |
| B14 | Tanpa email | ✅ 400 `email: ["This field is required."]` |
| B15 | Username 151 char | ✅ 400 `username: ["Ensure this field has no more than 150 characters."]` |
| B16 | User baru tanpa group | ✅ `groups.count() == 0` |
| B17 | Tidak ada session setelah register | ✅ 201, tanpa `sessionid` cookie |
| B18 | Response tidak bocorkan data | ✅ keys = `{"message"}` saja |
| **B19** | **Username `"bad user"` (spasi)** | 🔴 **201 — diterima!** (seharusnya 400). Format username tidak divalidasi |
| B20 | Register tanpa token CSRF | ✅ 201 (anonim, CSRF tidak ditegakkan) |
| B21 | Username tepat 7 char (boundary) | ✅ 201 |
| B22 | Password tepat 8 char valid (boundary) | ✅ 201 |

### C. Login
| Test | Skenario | Hasil |
|---|---|---|
| C01 | Login valid | ✅ 200 `{"message":"Berhasil Login","user_role":[],"user_id":7,"username":"loginuser1"}` + `sessionid` |
| C02 | User dengan group admin+staff | ✅ 200 `"user_role":["admin","staff"]` |
| C03 | Password salah | ✅ 400 `{"non_field_errors":["Username Atau Password Salah"]}` |
| C04 | User tidak ada | ✅ 400 pesan sama (no enumeration) |
| C05 | Tanpa username | ✅ 400 `username: ["This field is required."]` |
| C06 | Tanpa password | ✅ 400 `password: ["This field is required."]` |
| C07 | Body kosong | ✅ 400 kedua field required |
| C08 | User `is_active=False` | ✅ 400 pesan generik sama |
| C09 | Login content-type JSON | ✅ 200 |
| C10 | Tidak ada password di response | ✅ |
| C11 | 12× login valid beruntun | ✅ semua 200 → **tidak ada ScopedRateThrottle** (F-3) |
| C12 | CSRF cookie berputar setelah login | ✅ teramati (token lama ≠ token baru) |

### D. Axes lockout (brute-force protection)
| Test | Skenario | Hasil |
|---|---|---|
| D01 | 5× gagal, lalu password **benar** | ✅ 5× 400, lalu **429** `{"detail":"Account locked: too many login attempts. Please try again later."}` |
| D02 | Password salah saat terkunci | ✅ 429 |
| D03 | User lain saat satu user terkunci | ✅ 200 (lockout per username) |
| D04 | IP berbeda (`REMOTE_ADDR=10.9.9.9`) | ✅ 200 (lockout per IP) |
| D05 | Reset on success | ✅ 2× gagal → sukses → 5× gagal → 400 (count reset) → gagal ke-6 → 429 |

### E. Logout
| Test | Skenario | Hasil |
|---|---|---|
| E01 | Anonim | ✅ 403 `{"detail":"Authentication credentials were not provided."}` |
| E02 | Autentikasi tanpa token CSRF | ✅ 403 `{"detail":"CSRF Failed: CSRF token missing."}` |
| E03 | Session + token CSRF **segar** (pasca-login) | ✅ 204 (body kosong); session hilang → logout kedua → 403 |
| E04 | Token CSRF **stale** (dari sebelum login) | ✅ 403 `{"detail":"CSRF Failed: CSRF token from the 'X-Csrftoken' HTTP header incorrect."}` |
| E05 | GET `/logout/` | ✅ 403 (permission check sebelum method routing) |

### F. Method / verb
| Test | Skenario | Hasil |
|---|---|---|
| F01 | GET `/login/` | ✅ 405 `Method "GET" not allowed.` |
| F02 | GET `/register/` | ✅ 405 |
| F03 | HEAD `/login/` | ✅ 405 |
| F04 | OPTIONS `/login/` | ✅ 200 metadata (AllowAny) |
| F05 | OPTIONS `/logout/` anonim | ✅ 403 (metadata tidak bocor) |
| F06 | PUT `/login/` | ✅ 405 |

### G. Misc
| Test | Skenario | Hasil |
|---|---|---|
| G01 | POST tanpa trailing slash (`/auth/school/api/login`) | ✅ 301 redirect |
| G02 | Email beda case (`Existing@Mail.com`) | ✅ 201 (case-sensitive, lihat OBS-1) |

## Catatan integritas
- **Database dev tidak disentuh:** row count sebelum = sesudah (`auth_user=4`, `axes_accessattempt=0`, `django_session=1`, `axes_accesslog=41`).
- **Tidak ada file repo yang diubah/diedit:** `git status --porcelain` sebelum dan sesudah identik (hanya laporan `AUTH_RIPORT.md` ini yang baru ditulis, sesuai instruksi).
- Semua test berjalan di test DB `test_managemant_school` yang dibuat dan dihapus otomatis oleh Django test runner (termasuk data lockout, user, dan session uji).
