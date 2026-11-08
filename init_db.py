from database import get_db_connection


connection = get_db_connection()
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(30) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transaksi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jenis ENUM('pemasukan', 'pengeluaran') NOT NULL,
    nominal DECIMAL(15,2) NOT NULL,
    kategori VARCHAR(100) NOT NULL,
    deskripsi TEXT,
    tanggal DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_transaksi_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
)
""")

# Migrasi untuk tabel transaksi lama yang dibuat sebelum ada fitur login.
cursor.execute("""
SELECT COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'transaksi'
  AND COLUMN_NAME = 'user_id'
""")

if cursor.fetchone()[0] == 0:
    cursor.execute("""
    ALTER TABLE transaksi
        ADD COLUMN user_id INT NULL AFTER id,
        ADD CONSTRAINT fk_transaksi_user FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE
    """)
    print("Kolom user_id ditambahkan ke tabel transaksi.")

cursor.execute("SELECT COUNT(*) FROM transaksi WHERE user_id IS NULL")
transaksi_tanpa_pemilik = cursor.fetchone()[0]
if transaksi_tanpa_pemilik:
    print(
        f"Catatan: ada {transaksi_tanpa_pemilik} transaksi lama tanpa pemilik. "
        "Transaksi ini tidak akan tampil untuk user mana pun."
    )

connection.commit()

cursor.close()
connection.close()

print("Database dan tabel users serta transaksi berhasil dibuat.")
