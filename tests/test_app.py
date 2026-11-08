
import os
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

from app import app, validasi_transaksi, saldo_jadi_minus, format_rupiah


def test_format_rupiah():
    assert format_rupiah(1000000) == "Rp 1.000.000"


def test_validasi_transaksi_valid():
    form = {
        "jenis": "pemasukan",
        "nominal": "1000000",
        "kategori": "Gaji",
        "deskripsi": "Gaji bulanan",
        "tanggal": date.today().isoformat()
    }

    data, errors = validasi_transaksi(form)

    assert errors == []
    assert data["nominal"] == 1000000
    assert data["jenis"] == "pemasukan"


def test_validasi_jenis_transaksi_invalid():
    form = {
        "jenis": "transfer",
        "nominal": "100000",
        "kategori": "Lainnya",
        "deskripsi": "",
        "tanggal": date.today().isoformat()
    }

    data, errors = validasi_transaksi(form)

    assert any("jenis transaksi" in error.lower() for error in errors)


def test_validasi_nominal_nol():
    form = {
        "jenis": "pengeluaran",
        "nominal": "0",
        "kategori": "Makanan",
        "deskripsi": "",
        "tanggal": date.today().isoformat()
    }

    data, errors = validasi_transaksi(form)

    assert any("lebih dari 0" in error.lower() for error in errors)


def test_validasi_kategori_kosong():
    form = {
        "jenis": "pemasukan",
        "nominal": "100000",
        "kategori": "",
        "deskripsi": "",
        "tanggal": date.today().isoformat()
    }

    data, errors = validasi_transaksi(form)

    assert any("kategori wajib diisi" in error.lower() for error in errors)


def test_validasi_tanggal_masa_depan():
    form = {
        "jenis": "pemasukan",
        "nominal": "100000",
        "kategori": "Bonus",
        "deskripsi": "",
        "tanggal": (date.today() + timedelta(days=1)).isoformat()
    }

    data, errors = validasi_transaksi(form)

    assert any("tidak boleh melebihi hari ini" in error.lower() for error in errors)


def test_saldo_tidak_boleh_minus():
    assert saldo_jadi_minus(100000, -50000) is True


def test_saldo_boleh_bertambah():
    assert saldo_jadi_minus(100000, 150000) is False


def test_login_page_berhasil_diakses():
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/login")

    assert response.status_code == 200


def test_dashboard_memerlukan_login():
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_security_headers():
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.get("/login")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
