from database import get_db_connection


connection = get_db_connection()
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transaksi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jenis ENUM('pemasukan', 'pengeluaran') NOT NULL,
    nominal DECIMAL(15,2) NOT NULL,
    kategori VARCHAR(100) NOT NULL,
    deskripsi TEXT,
    tanggal DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

connection.commit()

cursor.close()
connection.close()

print("Database dan tabel transaksi berhasil dibuat.")