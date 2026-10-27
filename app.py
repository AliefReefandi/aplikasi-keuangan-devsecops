from flask import Flask, render_template, request, redirect, url_for
from database import get_db_connection

app = Flask(__name__)


@app.route("/")
def home():
    return "Aplikasi Keuangan DevSecOps berhasil dijalankan!"


@app.route("/test-db")
def test_db():
    try:
        connection = get_db_connection()
        connection.close()
        return "Koneksi ke database berhasil!"
    except Exception as e:
        return f"Koneksi database gagal: {e}"


@app.route("/transaksi", methods=["GET", "POST"])
def transaksi():
    if request.method == "POST":
        jenis = request.form["jenis"]
        nominal = request.form["nominal"]
        kategori = request.form["kategori"]
        deskripsi = request.form["deskripsi"]
        tanggal = request.form["tanggal"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO transaksi
            (jenis, nominal, kategori, deskripsi, tanggal)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            jenis,
            nominal,
            kategori,
            deskripsi,
            tanggal
        )

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("transaksi"))

    return render_template("transaksi.html")


@app.route("/riwayat")
def riwayat():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, jenis, nominal, kategori, deskripsi, tanggal
        FROM transaksi
        ORDER BY tanggal DESC, id DESC
    """)

    transaksi_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "riwayat.html",
        transaksi_list=transaksi_list
    )

@app.route("/transaksi/edit/<int:id>", methods=["GET", "POST"])
def edit_transaksi(id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        jenis = request.form["jenis"]
        nominal = request.form["nominal"]
        kategori = request.form["kategori"]
        deskripsi = request.form["deskripsi"]
        tanggal = request.form["tanggal"]

        query = """
            UPDATE transaksi
            SET jenis = %s,
                nominal = %s,
                kategori = %s,
                deskripsi = %s,
                tanggal = %s
            WHERE id = %s
        """

        values = (
            jenis,
            nominal,
            kategori,
            deskripsi,
            tanggal,
            id
        )

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("riwayat"))

    cursor.execute("""
        SELECT id, jenis, nominal, kategori, deskripsi, tanggal
        FROM transaksi
        WHERE id = %s
    """, (id,))

    transaksi = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "edit_transaksi.html",
        transaksi=transaksi
    )


@app.route("/transaksi/hapus/<int:id>", methods=["POST"])
def hapus_transaksi(id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM transaksi WHERE id = %s",
        (id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("riwayat"))


@app.route("/dashboard")
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN jenis = 'pemasukan' THEN nominal ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN jenis = 'pengeluaran' THEN nominal ELSE 0 END), 0)
        FROM transaksi
    """)

    total_pemasukan, total_pengeluaran = cursor.fetchone()

    saldo = total_pemasukan - total_pengeluaran

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        total_pemasukan=total_pemasukan,
        total_pengeluaran=total_pengeluaran,
        saldo=saldo
    )


if __name__ == "__main__":
    app.run(debug=True)