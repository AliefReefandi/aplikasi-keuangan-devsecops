# Incident Response Runbook — CatatUang

## 1. Tujuan

Dokumen ini menjelaskan prosedur penanganan insiden keamanan pada aplikasi CatatUang, khususnya aktivitas percobaan login gagal berulang (Brute Force Attack).

## 2. Deteksi Insiden

Insiden terdeteksi melalui Grafana Alerting dengan rule `Brute Force Login Detection`.

Alert akan aktif ketika jumlah percobaan login gagal melebihi 4 kali dalam 5 menit.

Notifikasi dikirim melalui email kepada administrator.

## 3. Prosedur Penanganan Insiden

**Tahap 1 — Identifikasi**

Administrator memeriksa notifikasi email Grafana dan membuka dashboard Security Monitoring untuk melihat aktivitas mencurigakan.

**Tahap 2 — Investigasi**

Administrator memeriksa Security Activity Logs melalui Grafana Explore dengan memperhatikan:
- IP address sumber aktivitas.
- Username yang digunakan.
- Waktu kejadian.
- Jumlah percobaan login gagal.

**Tahap 3 — Mitigasi**

Administrator melakukan tindakan berikut:
- Memastikan mekanisme rate limiting pada aplikasi berjalan.
- Membatasi akses dari sumber yang teridentifikasi mencurigakan melalui mekanisme keamanan yang tersedia.
- Menghubungi pemilik akun jika terdapat indikasi penyalahgunaan akun.
- Melakukan reset password dan pencabutan sesi apabila akun diduga telah dikompromikan.

**Tahap 4 — Pemulihan**

Administrator memastikan aplikasi dapat diakses kembali, mekanisme login berjalan normal, dan tidak terdapat aktivitas mencurigakan lanjutan.

**Tahap 5 — Dokumentasi**

Administrator menyimpan bukti alert, log aktivitas, waktu kejadian, tindakan mitigasi, dan hasil penanganan insiden.

## 4. Monitoring Setelah Insiden

Setelah insiden ditangani, administrator memantau dashboard Grafana dan memastikan tidak terdapat peningkatan percobaan login gagal yang mencurigakan.

## 5. Evaluasi

Hasil penanganan insiden digunakan untuk mengevaluasi efektivitas mekanisme keamanan aplikasi dan menentukan perbaikan yang diperlukan.S