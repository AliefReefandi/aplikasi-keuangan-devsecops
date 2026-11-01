import logging
import os
import re
import secrets
from contextlib import contextmanager
from datetime import date, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler

import mysql.connector
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_connection

app = Flask(__name__)

if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY belum diatur di file .env")

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    MAX_CONTENT_LENGTH=16 * 1024,
)

# Membatasi jumlah request per alamat IP untuk mencegah brute force
# dan gangguan ketersediaan aplikasi (Threat #6).
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
)

# Log keamanan untuk tahap Monitor: login, akses ditolak, perubahan data.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)
if not security_logger.handlers:
    log_format = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "security.log"),
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)
    security_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    security_logger.addHandler(console_handler)

JENIS_VALID = ("pemasukan", "pengeluaran")
NOMINAL_MAKS = 999_999_999_999
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{3,30}")
NOMINAL_PATTERN = re.compile(r"[0-9]{1,12}")
KARAKTER_KONTROL = re.compile(r"[\r\n\t]")

KATEGORI_SARAN = {
    "pemasukan": ["Gaji", "Bonus", "Uang Saku", "Penjualan", "Investasi", "Hadiah", "Lainnya"],
    "pengeluaran": ["Makanan", "Transportasi", "Belanja", "Tagihan", "Hiburan",
                    "Kesehatan", "Pendidikan", "Lainnya"],
}

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

# Dipakai saat username tidak ditemukan agar waktu respons login tetap sama
# (mencegah enumerasi username lewat timing).
DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_hex(16))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

@contextmanager
def buka_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True, buffered=True)
    try:
        yield connection, cursor
    finally:
        cursor.close()
        connection.close()


def format_rupiah(nilai):
    return "Rp " + f"{nilai:,.0f}".replace(",", ".")


def format_tanggal(tanggal):
    return f"{tanggal.day} {BULAN[tanggal.month - 1]} {tanggal.year}"


def catat_keamanan(event, level=logging.INFO, **detail):
    info = {"ip": request.remote_addr, "user_id": session.get("user_id"), **detail}
    # Karakter baris baru dibuang agar input pengguna tidak bisa memalsukan baris log.
    teks = " ".join(
        f"{kunci}={KARAKTER_KONTROL.sub('_', str(nilai))}" for kunci, nilai in info.items()
    )
    security_logger.log(level, "%s %s", event, teks)


app.jinja_env.filters["rupiah"] = format_rupiah
app.jinja_env.filters["tanggal"] = format_tanggal


def get_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = get_csrf_token


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def kunci_user(cursor, user_id):
    # Mengunci baris user sampai commit, sehingga dua request bersamaan
    # tidak bisa sama-sama lolos pengecekan saldo.
    cursor.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user_id,))
    cursor.fetchone()


def hitung_saldo(cursor, user_id):
    cursor.execute("""
        SELECT COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN nominal ELSE -nominal END), 0) AS saldo
        FROM transaksi
        WHERE user_id = %s
    """, (user_id,))
    return cursor.fetchone()["saldo"]


def ambil_transaksi(cursor, id, user_id):
    cursor.execute("""
        SELECT id, jenis, nominal, kategori, deskripsi, tanggal
        FROM transaksi
        WHERE id = %s AND user_id = %s
    """, (id, user_id))
    return cursor.fetchone()


def efek_saldo(jenis, nominal):
    return nominal if jenis == "pemasukan" else -nominal


def saldo_jadi_minus(saldo_awal, saldo_akhir):
    # Perubahan ditolak jika membuat saldo minus. Perubahan yang justru
    # menaikkan saldo tetap diizinkan.
    return saldo_akhir < 0 and saldo_akhir < saldo_awal


def validasi_transaksi(form):
    errors = []

    jenis = form.get("jenis", "")
    if jenis not in JENIS_VALID:
        errors.append("Pilih jenis transaksi: pemasukan atau pengeluaran.")

    nominal = None
    nominal_teks = form.get("nominal", "").replace(".", "").strip()
    if not NOMINAL_PATTERN.fullmatch(nominal_teks):
        errors.append("Nominal harus berupa angka bulat, maksimal Rp 999.999.999.999.")
    else:
        nominal = int(nominal_teks)
        if nominal <= 0:
            errors.append("Nominal harus lebih dari 0.")

    kategori = form.get("kategori", "").strip()
    if not kategori:
        errors.append("Kategori wajib diisi.")
    elif len(kategori) > 100:
        errors.append("Kategori maksimal 100 karakter.")

    deskripsi = form.get("deskripsi", "").strip()
    if len(deskripsi) > 500:
        errors.append("Deskripsi maksimal 500 karakter.")

    tanggal = None
    try:
        tanggal = date.fromisoformat(form.get("tanggal", ""))
    except ValueError:
        errors.append("Tanggal tidak valid.")
    else:
        if tanggal > date.today():
            errors.append("Tanggal transaksi tidak boleh melebihi hari ini.")

    data = {
        "jenis": jenis,
        "nominal": nominal,
        "kategori": kategori,
        "deskripsi": deskripsi,
        "tanggal": tanggal,
    }
    return data, errors


def render_form_transaksi(template, form, saldo_awal, saldo_dasar, errors=None, status=200, **context):
    return render_template(
        template,
        form=form,
        errors=errors or [],
        saldo_awal=saldo_awal,
        saldo_dasar=saldo_dasar,
        kategori_saran=KATEGORI_SARAN,
        hari_ini=date.today().isoformat(),
        **context
    ), status


# ---------------------------------------------------------------------------
# Keamanan request/response
# ---------------------------------------------------------------------------

@app.before_request
def cek_csrf():
    if request.method != "POST":
        return None

    token_session = session.get("csrf_token")
    token_form = request.form.get("csrf_token", "")
    if not token_session or not secrets.compare_digest(token_form, token_session):
        catat_keamanan("CSRF_DITOLAK", logging.WARNING, path=request.path)
        flash("Sesi formulir sudah kedaluwarsa. Silakan coba lagi.", "warning")
        return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))
    return None


@app.after_request
def tambah_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
    )
    if request.endpoint != "static":
        # Data keuangan tidak boleh tersimpan di cache browser,
        # sehingga tidak bisa dilihat lagi dengan tombol back setelah logout.
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(404)
def halaman_tidak_ditemukan(error):
    return render_template(
        "error.html",
        kode=404,
        pesan="Halaman atau data yang Anda cari tidak ditemukan."
    ), 404


@app.errorhandler(413)
def request_terlalu_besar(error):
    return render_template(
        "error.html",
        kode=413,
        pesan="Data yang dikirim terlalu besar."
    ), 413


@app.errorhandler(429)
def terlalu_banyak_percobaan(error):
    catat_keamanan("RATE_LIMIT", logging.WARNING, path=request.path)
    return render_template(
        "error.html",
        kode=429,
        pesan="Terlalu banyak percobaan. Silakan tunggu 1 menit lalu coba lagi."
    ), 429


# ---------------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        konfirmasi = request.form.get("konfirmasi_password", "")

        errors = []
        if not USERNAME_PATTERN.fullmatch(username):
            errors.append("Username harus 3–30 karakter dan hanya berisi huruf, angka, atau garis bawah (_).")
        if len(password) < 8 or len(password) > 128:
            errors.append("Password harus 8–128 karakter.")
        elif not (re.search(r"[A-Za-z]", password) and re.search(r"[0-9]", password)):
            errors.append("Password harus mengandung huruf dan angka.")
        if password != konfirmasi:
            errors.append("Konfirmasi password tidak sama.")

        if not errors:
            with buka_db() as (connection, cursor):
                try:
                    cursor.execute(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                        (username, generate_password_hash(password))
                    )
                    connection.commit()
                except mysql.connector.IntegrityError:
                    errors.append("Username sudah digunakan. Silakan pilih username lain.")

        if errors:
            return render_template("register.html", errors=errors, username=username), 400

        catat_keamanan("REGISTER_BERHASIL", username=username)
        flash("Akun berhasil dibuat. Silakan login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", errors=[])


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with buka_db() as (connection, cursor):
            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()

        password_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
        password_benar = check_password_hash(password_hash, password)

        if user is None or not password_benar:
            catat_keamanan("LOGIN_GAGAL", logging.WARNING, username=username)
            return render_template(
                "login.html",
                errors=["Username atau password salah."],
                username=username
            ), 401

        # Session lama dibuang untuk mencegah session fixation.
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        catat_keamanan("LOGIN_BERHASIL", username=user["username"])
        flash(f"Selamat datang, {user['username']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", errors=[])


@app.route("/logout", methods=["POST"])
def logout():
    catat_keamanan("LOGOUT")
    session.clear()
    flash("Anda telah keluar.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Fitur keuangan
# ---------------------------------------------------------------------------

@app.route("/test-db")
def test_db():
    try:
        connection = get_db_connection()
        connection.close()
        return "Koneksi ke database berhasil!"
    except Exception:
        app.logger.exception("Koneksi database gagal")
        return "Koneksi database gagal.", 500


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]

    with buka_db() as (connection, cursor):
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN nominal ELSE 0 END), 0) AS total_pemasukan,
                COALESCE(SUM(CASE WHEN jenis = 'pengeluaran' THEN nominal ELSE 0 END), 0) AS total_pengeluaran
            FROM transaksi
            WHERE user_id = %s
        """, (user_id,))
        ringkasan = cursor.fetchone()

        cursor.execute("""
            SELECT id, jenis, nominal, kategori, deskripsi, tanggal
            FROM transaksi
            WHERE user_id = %s
            ORDER BY tanggal DESC, id DESC
            LIMIT 5
        """, (user_id,))
        transaksi_terbaru = cursor.fetchall()

    total_pemasukan = ringkasan["total_pemasukan"]
    total_pengeluaran = ringkasan["total_pengeluaran"]
    saldo = total_pemasukan - total_pengeluaran

    rasio_pengeluaran = 0
    if total_pemasukan > 0:
        rasio_pengeluaran = min(round(total_pengeluaran / total_pemasukan * 100), 100)

    return render_template(
        "dashboard.html",
        total_pemasukan=total_pemasukan,
        total_pengeluaran=total_pengeluaran,
        saldo=saldo,
        rasio_pengeluaran=rasio_pengeluaran,
        transaksi_terbaru=transaksi_terbaru
    )


@app.route("/transaksi", methods=["GET", "POST"])
@login_required
def transaksi():
    user_id = session["user_id"]

    with buka_db() as (connection, cursor):
        if request.method == "POST":
            kunci_user(cursor, user_id)

        saldo = hitung_saldo(cursor, user_id)

        if request.method == "GET":
            form = {"tanggal": date.today().isoformat()}
            return render_form_transaksi("transaksi.html", form, saldo, saldo)

        data, errors = validasi_transaksi(request.form)

        if not errors:
            saldo_akhir = saldo + efek_saldo(data["jenis"], data["nominal"])
            if saldo_jadi_minus(saldo, saldo_akhir):
                errors.append(
                    f"Saldo tidak mencukupi. Saldo Anda saat ini {format_rupiah(saldo)}, "
                    f"sedangkan pengeluaran yang dimasukkan {format_rupiah(data['nominal'])}."
                )

        if errors:
            catat_keamanan("TRANSAKSI_DITOLAK", logging.WARNING, aksi="tambah", alasan=errors[0])
            return render_form_transaksi(
                "transaksi.html", request.form, saldo, saldo, errors, status=400
            )

        cursor.execute("""
            INSERT INTO transaksi
            (user_id, jenis, nominal, kategori, deskripsi, tanggal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            data["jenis"],
            data["nominal"],
            data["kategori"],
            data["deskripsi"],
            data["tanggal"]
        ))
        connection.commit()
        transaksi_id = cursor.lastrowid

    catat_keamanan(
        "TRANSAKSI_DITAMBAH", transaksi_id=transaksi_id, jenis=data["jenis"], nominal=data["nominal"]
    )
    flash("Transaksi berhasil ditambahkan.", "success")
    return redirect(url_for("riwayat", baru=transaksi_id))


@app.route("/riwayat")
@login_required
def riwayat():
    user_id = session["user_id"]
    filter_jenis = request.args.get("jenis", "")
    if filter_jenis not in JENIS_VALID:
        filter_jenis = ""

    query = """
        SELECT id, jenis, nominal, kategori, deskripsi, tanggal
        FROM transaksi
        WHERE user_id = %s
    """
    params = [user_id]
    if filter_jenis:
        query += " AND jenis = %s"
        params.append(filter_jenis)
    query += " ORDER BY tanggal DESC, id DESC"

    with buka_db() as (connection, cursor):
        cursor.execute(query, params)
        transaksi_list = cursor.fetchall()

    return render_template(
        "riwayat.html",
        transaksi_list=transaksi_list,
        filter_jenis=filter_jenis,
        transaksi_baru=request.args.get("baru", type=int)
    )


@app.route("/transaksi/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_transaksi(id):
    user_id = session["user_id"]

    with buka_db() as (connection, cursor):
        if request.method == "POST":
            kunci_user(cursor, user_id)

        transaksi = ambil_transaksi(cursor, id, user_id)
        if transaksi is None:
            catat_keamanan("AKSES_TRANSAKSI_DITOLAK", logging.WARNING, aksi="edit", transaksi_id=id)
            abort(404)

        saldo = hitung_saldo(cursor, user_id)
        saldo_tanpa_transaksi = saldo - efek_saldo(transaksi["jenis"], transaksi["nominal"])

        if request.method == "GET":
            form = {
                "jenis": transaksi["jenis"],
                "nominal": f"{transaksi['nominal']:,.0f}".replace(",", "."),
                "kategori": transaksi["kategori"],
                "deskripsi": transaksi["deskripsi"] or "",
                "tanggal": transaksi["tanggal"].isoformat(),
            }
            return render_form_transaksi(
                "edit_transaksi.html", form, saldo, saldo_tanpa_transaksi, transaksi=transaksi
            )

        data, errors = validasi_transaksi(request.form)

        if not errors:
            saldo_akhir = saldo_tanpa_transaksi + efek_saldo(data["jenis"], data["nominal"])
            if saldo_jadi_minus(saldo, saldo_akhir):
                errors.append(
                    f"Perubahan ditolak karena saldo akan menjadi minus ({format_rupiah(saldo_akhir)}). "
                    f"Saldo tersedia tanpa transaksi ini: {format_rupiah(saldo_tanpa_transaksi)}."
                )

        if errors:
            catat_keamanan(
                "TRANSAKSI_DITOLAK", logging.WARNING, aksi="edit", transaksi_id=id, alasan=errors[0]
            )
            return render_form_transaksi(
                "edit_transaksi.html", request.form, saldo, saldo_tanpa_transaksi, errors,
                status=400, transaksi=transaksi
            )

        cursor.execute("""
            UPDATE transaksi
            SET jenis = %s,
                nominal = %s,
                kategori = %s,
                deskripsi = %s,
                tanggal = %s
            WHERE id = %s AND user_id = %s
        """, (
            data["jenis"],
            data["nominal"],
            data["kategori"],
            data["deskripsi"],
            data["tanggal"],
            id,
            user_id
        ))
        connection.commit()

    catat_keamanan("TRANSAKSI_DIUBAH", transaksi_id=id)
    flash("Transaksi berhasil diperbarui.", "success")
    return redirect(url_for("riwayat", baru=id))


@app.route("/transaksi/hapus/<int:id>", methods=["POST"])
@login_required
def hapus_transaksi(id):
    user_id = session["user_id"]

    with buka_db() as (connection, cursor):
        kunci_user(cursor, user_id)

        transaksi = ambil_transaksi(cursor, id, user_id)
        if transaksi is None:
            catat_keamanan("AKSES_TRANSAKSI_DITOLAK", logging.WARNING, aksi="hapus", transaksi_id=id)
            abort(404)

        saldo = hitung_saldo(cursor, user_id)
        saldo_akhir = saldo - efek_saldo(transaksi["jenis"], transaksi["nominal"])
        if saldo_jadi_minus(saldo, saldo_akhir):
            catat_keamanan(
                "TRANSAKSI_DITOLAK", logging.WARNING, aksi="hapus", transaksi_id=id, alasan="saldo minus"
            )
            flash(
                f"Transaksi tidak dapat dihapus karena saldo akan menjadi minus "
                f"({format_rupiah(saldo_akhir)}).",
                "error"
            )
            return redirect(url_for("riwayat"))

        cursor.execute(
            "DELETE FROM transaksi WHERE id = %s AND user_id = %s",
            (id, user_id)
        )
        connection.commit()

    catat_keamanan("TRANSAKSI_DIHAPUS", transaksi_id=id)
    flash("Transaksi berhasil dihapus.", "success")
    return redirect(url_for("riwayat"))


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
