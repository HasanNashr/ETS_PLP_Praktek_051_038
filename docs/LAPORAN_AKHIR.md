# Laporan Akhir

## 1. Hasil evaluasi

Tempel keluaran `python evaluate.py` setelah `data/ground_truth.csv` dilengkapi.

```text
Dievaluasi: audit.sql, campuran_error.sql, laporan_penjualan.sql, pemeliharaan.sql (27 triple)

Metode   Precision  Recall     F1
parser        1.00    1.00   1.00
regex         0.65    0.81   0.72

[regex]
  salah ditemukan (FP): ('audit.sql', 16, 'sesi', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 4, 'pesanan', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 8, 'keranjang', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'D')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pesanan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'rahasia', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 15, 'pesanan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.alamat', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.pelanggan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'pelanggan_lama', 'U')
  salah ditemukan (FP): ('pemeliharaan.sql', 15, 'crm.alamat', 'R')
  terlewat (FN):       ('audit.sql', 2, 'pesanan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pelanggan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pesanan', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.alamat', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.pelanggan', 'R')
```

## 2. Tiga kasus di mana regex salah

Untuk tiap kasus: SQL-nya, kesalahan regex, dan mengapa parser benar (kaitkan dengan konsep
lexing, parsing, atau resolusi).

1. **`laporan_penjualan.sql` baris 2 — komentar dianggap statement oleh regex.**
   SQL: `-- DELETE FROM pelanggan   (baris ini komentar, bukan perintah)`.
   Regex mendeteksi `DELETE` dan `FROM pelanggan` di dalam komentar, menghasilkan FP `('laporan_penjualan.sql', 2, 'pelanggan', 'D')` dan FP `('laporan_penjualan.sql', 2, 'pelanggan', 'R')`.
   Parser benar karena **lexer** (Crafting Interpreters bab 4) membuang komentar saat scanning, sehingga token `DELETE` dan `FROM` dari baris komentar tidak pernah masuk ke parser. Regex tidak memiliki fase lexing yang memisahkan komentar dari kode.

2. **`laporan_penjualan.sql` baris 6 — string literal dianggap referensi tabel oleh regex.**
   SQL: `WHERE o.status = 'LUNAS' AND o.catatan <> 'FROM rahasia'`.
   Regex mendeteksi `FROM rahasia` di dalam string literal, menghasilkan FP `('laporan_penjualan.sql', 2, 'rahasia', 'R')`.
   Parser benar karena **lexer** mengenali `'FROM rahasia'` sebagai satu token `STRING`, bukan keyword `FROM` diikuti identifier. Tanpa lexing yang benar, regex tidak bisa membedakan keyword di dalam string dari keyword di luar string.

3. **`pemeliharaan.sql` baris 2 — komentar blok dianggap statement oleh regex.**
   SQL: `/* ... UPDATE pelanggan_lama sudah tidak dipakai. */`.
   Regex mendeteksi `UPDATE pelanggan_lama` di dalam komentar blok, menghasilkan FP `('pemeliharaan.sql', 2, 'pelanggan_lama', 'U')`.
   Parser benar karena lexer mengimplementasi komentar blok `/* ... */` dan membuang seluruh isinya. Regex berbasis pola teks tidak memahami konteks sintaktis — tidak bisa membedakan keyword di dalam komentar blok dari keyword di kode aktif.

## 3. Batas pendekatan kami

Minimal tiga hal yang **tidak bisa** ditangani dengan benar oleh tool ini meskipun semua bug
sudah diperbaiki. Untuk tiap batas: contoh SQL atau situasinya, akibatnya pada CRUD matrix,
dan informasi apa yang dibutuhkan untuk mengatasinya.

1. **CTE (Common Table Expressions) dengan `WITH`.**
   Contoh: `WITH active AS (SELECT id FROM pelanggan WHERE aktif = 1) SELECT * FROM active JOIN pesanan ON pesanan.pelanggan_id = active.id`.
   Akibat: Parser akan gagal karena `WITH` bukan keyword yang dikenali. CTE tidak masuk CRUD matrix sama sekali.
   Dibutuhkan: Menambah `WITH` ke grammar, mem-parse CTE sebagai subquery bernama, dan mendaftarkannya di scope resolver.

2. **`UNION` / `UNION ALL` antar SELECT.**
   Contoh: `SELECT id FROM pelanggan UNION SELECT id FROM supplier`.
   Akibat: Parser hanya mem-parse SELECT pertama; `UNION SELECT ...` menyebabkan parse error. Tabel `supplier` tidak terdeteksi.
   Dibutuhkan: Menambah aturan grammar untuk `UNION` dan memperlakukan hasilnya sebagai gabungan dari beberapa SELECT.

3. **Qualified wildcard `t.*` di SELECT list.**
   Contoh: `SELECT p.* FROM pelanggan p`.
   Akibat: Parser mencoba mem-parse `p.*` sebagai `ColumnRef(p) * ...` (perkalian), yang gagal atau salah. Kolom-kolom dari tabel `p` tidak tercatat di column_usage.
   Dibutuhkan: Menambah aturan khusus di `_select_list()` untuk mengenali pola `IDENT DOT STAR` sebagai qualified wildcard, bukan ekspresi perkalian.

## 4. Pembagian kerja

**Hasan Nashrullah (051):** Bertanggung jawab atas modul Lexer dan Parser.
- Memperbaiki bug B1 (keyword case-insensitive), B2 (escaped quotes), B3 (operator `<>`), B5 (error recovery), B6 (LEFT OUTER JOIN).
- Menyelesaikan TODO T1 (INSERT...SELECT) dan T3 (komentar blok).
- Menulis test regresi untuk bug yang diperbaiki.

**Amor Azzam Imani (038):** Bertanggung jawab atas modul Resolver dan Analyzer.
- Memperbaiki bug B4 (precedence AND/OR), B7 (delete scope leak), B8 (lookup order), B9 (UPDATE subquery op).
- Menyelesaikan TODO T2 (kolom tanpa qualifier).
- Menulis test regresi dan 5 test kasus tepi.
- Melengkapi ground_truth.csv.

**Bersama:** Mengisi laporan bug, kartu desain, laporan akhir, dan log AI. Saling menjelaskan bagian yang dikerjakan partner untuk persiapan demo.
