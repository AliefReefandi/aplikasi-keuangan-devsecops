# Rollback Procedure — CatatUang

## 1. Tujuan

Dokumen ini menjelaskan prosedur mengembalikan aplikasi CatatUang ke versi sebelumnya apabila deployment terbaru mengalami masalah atau menyebabkan aplikasi tidak dapat berjalan dengan normal.

## 2. Strategi Rollback

Aplikasi menggunakan Docker Image Versioning untuk menyimpan versi aplikasi yang dapat digunakan kembali.

Versi stabil yang tersedia:

- Image: `catatuang-app:v1.0.0-security-monitoring`
- Git Tag: `v1.0.0-security-monitoring`
- Git Commit: `42677a5`

Versi image dipilih melalui variabel `APP_IMAGE` pada file `.env`.

## 3. Prosedur Rollback

### Tahap 1 — Identifikasi Masalah

Administrator memeriksa kondisi aplikasi melalui Docker Compose.

```powershell
docker compose ps
docker compose logs --tail=50 app
```

Jika ditemukan masalah pada deployment, administrator menentukan versi aplikasi yang akan digunakan untuk pemulihan.

### Tahap 2 — Memilih Versi Stabil

Buka file `.env` dan ubah variabel berikut:

```env
APP_IMAGE=catatuang-app:v1.0.0-security-monitoring
```

Pastikan image tersebut masih tersedia secara lokal.

```powershell
docker images catatuang-app
```

### Tahap 3 — Menjalankan Rollback

Terapkan konfigurasi menggunakan Docker Compose:

```powershell
docker compose up -d app
```

Docker Compose akan menjalankan ulang service aplikasi menggunakan image yang telah dipilih.

### Tahap 4 — Verifikasi

Periksa image yang digunakan container:

```powershell
docker inspect aplikasi-keuangan-devsecops-app-1 --format '{{.Config.Image}}'
```

Periksa kondisi seluruh container:

```powershell
docker compose ps
```

Periksa log aplikasi:

```powershell
docker compose logs --tail=50 app
```

Administrator juga perlu menguji login, dashboard, dan riwayat transaksi.

## 4. Perlindungan Database

Rollback aplikasi tidak boleh menghapus data transaksi pengguna.

Volume database `db_data` harus tetap dipertahankan selama proses rollback.

Hindari menjalankan perintah berikut:

```powershell
docker compose down -v
```

Perintah tersebut dapat menghapus volume yang menyimpan data database.

## 5. Kriteria Keberhasilan Rollback

Rollback dinyatakan berhasil apabila:

1. Container aplikasi berjalan dengan status Up.
2. Image yang digunakan sesuai dengan versi stabil yang dipilih.
3. Container MySQL berstatus Healthy.
4. Pengguna dapat melakukan login.
5. Dashboard dan riwayat transaksi dapat diakses.
6. Data transaksi sebelumnya tetap tersedia.

## 6. Catatan Pengujian

Pengujian rollback dilakukan dengan mengganti image dari `v1.0.0-security-monitoring` ke `v1.1.0-test`, kemudian mengembalikannya ke versi stabil.

Kedua tag simulasi menggunakan image yang sama. Pengujian ini membuktikan mekanisme pemilihan versi image dan pemulihan konfigurasi Docker Compose, tetapi belum menguji pemulihan dari kerusakan aplikasi yang sebenarnya.