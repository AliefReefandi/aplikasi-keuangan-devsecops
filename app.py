from flask import Flask
import mysql.connector

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="root123",
        database="keuangan"
    )


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


if __name__ == "__main__":
    app.run(debug=True)