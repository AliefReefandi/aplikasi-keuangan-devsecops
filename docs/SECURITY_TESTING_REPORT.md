# SECURITY TESTING REPORT
## Secure Personal Finance Management Application

### 1. Informasi Pengujian

| Informasi | Keterangan |
|---|---|
| Nama aplikasi | CatatUang |
| Jenis pengujian | Security Testing |
| Tanggal pengujian | 23 November 2026 |
| Environment | Docker Desktop |
| Backend | Flask |
| Database | MySQL 8.0 |
| Web Server | Gunicorn |
| Branch | feature-part-b-security-testing |

### 2. Tujuan Pengujian

Security Testing dilakukan untuk mengevaluasi mekanisme keamanan aplikasi CatatUang, khususnya perlindungan terhadap SQL Injection, Cross-Site Scripting (XSS), akses tidak sah, penyalahgunaan autentikasi, Cross-Site Request Forgery (CSRF), dan keamanan HTTP response headers.

### 3. Hasil Pengujian

#### 3.1 SQL Injection

**Pengujian Login**

Payload:
`' OR '1'='1' --`

Hasil: Aplikasi menolak percobaan login dan menampilkan pesan username atau password salah.

Analisis: Query login menggunakan parameterized query dengan placeholder `%s`, sehingga input pengguna tidak digabungkan langsung ke perintah SQL.

**Pengujian Filter Riwayat**

Payload:
`' OR '1'='1' --`

Hasil: Halaman riwayat tetap berjalan normal dan tidak menampilkan error SQL.

Analisis: Parameter `jenis` divalidasi menggunakan `JENIS_VALID`. Input yang tidak valid dikosongkan sebelum digunakan dalam query.

Kesimpulan: Tidak ditemukan indikasi SQL Injection pada kedua skenario yang diuji.

#### 3.2 Cross-Site Scripting (XSS)

Payload:
`<script>alert('XSS Test')</script>`

Lokasi pengujian:
- Deskripsi transaksi pada halaman Riwayat.
- Kolom deskripsi pada halaman Edit Transaksi.

Hasil: Payload ditampilkan sebagai teks biasa dan tidak mengeksekusi JavaScript. Tidak muncul pop-up XSS.

Kesimpulan: Perlindungan terhadap XSS bekerja pada kedua skenario yang diuji.

#### 3.3 Authentication Testing

Pengujian dilakukan dengan logout dari aplikasi, kemudian mencoba mengakses endpoint `/dashboard` secara langsung.

Hasil: Aplikasi mengarahkan pengguna kembali ke halaman login.

Analisis: Endpoint dashboard dilindungi oleh mekanisme `login_required`.

Kesimpulan: Pengguna yang belum terautentikasi tidak dapat mengakses dashboard pada skenario pengujian.

#### 3.4 Broken Access Control / IDOR

Pengujian menggunakan dua akun:
- Akun A: Reefandi.
- Akun B: UserTestB.

Transaksi milik akun B memiliki ID 21.

Pengujian dilakukan dengan login menggunakan akun A, kemudian mencoba mengakses:

`/transaksi/edit/21`

Hasil: Aplikasi menampilkan HTTP 404 dan menolak akses terhadap transaksi milik akun B.

Selain itu, transaksi akun B tidak muncul dalam riwayat akun A.

Analisis: Backend menggunakan kombinasi ID transaksi dan user_id untuk mengambil data transaksi.

Kesimpulan: Isolasi data antar pengguna berjalan pada skenario yang diuji.

#### 3.5 Proteksi Endpoint Penghapusan

Pemeriksaan dilakukan melalui analisis kode fungsi `hapus_transaksi()`.

Ditemukan pemeriksaan kepemilikan transaksi menggunakan `ambil_transaksi(cursor, id, user_id)` sebelum penghapusan dilakukan.

Query DELETE juga menggunakan parameter:

`DELETE FROM transaksi WHERE id = %s AND user_id = %s`

Kesimpulan: Implementasi kode telah membatasi penghapusan berdasarkan kepemilikan transaksi. Pengujian langsung terhadap endpoint penghapusan lintas pengguna belum dilakukan.

#### 3.6 Rate Limiting

Konfigurasi yang ditemukan:
- Registrasi: 3 request per menit.
- Login: 5 request per menit.

Pengujian login dilakukan menggunakan akun pengujian dengan password yang salah.

Hasil:
- Lima percobaan login gagal tercatat.
- Percobaan berikutnya terkena pembatasan.
- Browser menampilkan HTTP 429 Too Many Requests.
- Log aplikasi mencatat `RATE_LIMIT`.

Kesimpulan: Rate limiting login berhasil diuji secara langsung.

#### 3.7 Cross-Site Request Forgery (CSRF)

Pengujian dilakukan dengan mengirimkan HTTP POST ke endpoint `/login` tanpa menyertakan token CSRF.

Hasil:
- HTTP Response: 302 FOUND.
- Redirect: `/login`.
- Aplikasi mencatat `CSRF_DITOLAK`.

Analisis: Fungsi `cek_csrf()` memeriksa token pada session dan form menggunakan `secrets.compare_digest()`.

Kesimpulan: Request POST tanpa token CSRF yang valid berhasil ditolak.

#### 3.8 Security Headers

Pemeriksaan dilakukan menggunakan perintah:

`curl.exe -I http://localhost:5000`

Header yang ditemukan:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: same-origin
- Content-Security-Policy
- Cross-Origin-Opener-Policy: same-origin
- Cross-Origin-Resource-Policy: same-origin
- Cross-Origin-Embedder-Policy: require-corp
- Permissions-Policy
- Cache-Control: no-store

Kesimpulan: Header keamanan ditemukan pada HTTP response yang diuji.

### 4. Rekapitulasi Hasil

| No. | Pengujian | Hasil |
|---|---|---|
| 1 | SQL Injection Login | Tidak ditemukan indikasi kerentanan |
| 2 | SQL Injection Riwayat | Tidak ditemukan indikasi kerentanan |
| 3 | XSS Deskripsi Transaksi | Tidak berhasil dieksekusi |
| 4 | XSS Halaman Edit | Tidak berhasil dieksekusi |
| 5 | Authentication Testing | Berhasil dilindungi |
| 6 | Broken Access Control / IDOR | Akses ditolak |
| 7 | Isolasi Data Pengguna | Berjalan sesuai harapan |
| 8 | Proteksi Endpoint Penghapusan | Terverifikasi melalui pemeriksaan kode |
| 9 | Rate Limiting | Berhasil diuji |
| 10 | CSRF Protection | Berhasil diuji |
| 11 | Security Headers | Ditemukan pada response |

### 5. Kesimpulan

Berdasarkan pengujian yang telah dilakukan, aplikasi CatatUang telah menerapkan beberapa mekanisme keamanan, seperti parameterized query, validasi input, autentikasi pengguna, pembatasan akses berdasarkan kepemilikan data, rate limiting, CSRF token, serta HTTP security headers.

Seluruh skenario pengujian langsung memberikan hasil sesuai perlindungan yang diharapkan. Pemeriksaan kode juga menunjukkan adanya pembatasan kepemilikan pada endpoint penghapusan transaksi.

Namun, hasil ini terbatas pada skenario dan environment pengujian yang dilakukan. Pengujian ini belum dapat menjamin bahwa seluruh kemungkinan kerentanan keamanan telah ditemukan atau ditangani.

### 6. Bukti Pengujian

Seluruh screenshot dan bukti pendukung disimpan dalam direktori:

`evidence/part-b/`

Bukti tersebut mencakup hasil pengujian SQL Injection, XSS, autentikasi, kontrol akses, rate limiting, CSRF, dan security headers.