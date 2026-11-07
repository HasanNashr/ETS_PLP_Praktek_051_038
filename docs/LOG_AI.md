# Log Penggunaan AI

Catat setiap penggunaan AI atau coding agent yang memengaruhi kode atau laporan.

| No | Siapa | Prompt / tugas (ringkas) | Hasil: diterima, diubah, atau ditolak | Alasan | Cara verifikasi |
| --- | --- | --- | --- | --- | --- |
| 1 | Hasan Nashrullah | Baca semua file codebase dan identifikasi bug serta TODO | Diterima — AI mengidentifikasi 9 bug dan 3 TODO | AI membandingkan kode dengan SPESIFIKASI.md secara sistematis, menghemat waktu eksplorasi awal | Diverifikasi manual satu per satu: setiap bug dicek dengan membaca kode terkait dan menjalankan test |
| 2 | Hasan Nashrullah | Fix bug lexer: keyword case-insensitive, escaped quotes, komentar blok, operator `<>` | Diterima dengan modifikasi — kode AI diadaptasi ke gaya kode asli | Logika fix benar tapi format perlu disesuaikan | Dijalankan `python -m pytest tests/test_lexer.py -v` — 9/9 passed |
| 3 | Hasan Nashrullah | Fix parser: INSERT...SELECT, LEFT OUTER JOIN, error recovery, precedence AND/OR | Diterima — AI menyarankan pisah `_logical()` jadi `_or()` dan `_and()` | Sesuai pola Crafting Interpreters bab 6 | Dijalankan semua test parser + verifikasi AST output pada semua file sample |
| 4 | Amor Azzam Imani | Fix resolver: `_pop()` di delete, lookup order, kolom tanpa qualifier | Diterima — logika resolver sesuai spesifikasi §4 | AI menunjukkan pola yang benar di `_update()` sebagai referensi untuk `_delete()` | Dijalankan test resolver + verifikasi dengan `--ast` pada audit.sql |
| 5 | Amor Azzam Imani | Fix analyzer: UPDATE subquery operasi "R" bukan "U" | Diterima — perubahan minimal dan jelas | Sesuai spesifikasi §5: subquery selalu R | Diverifikasi dengan `crud()` helper dan CRUD matrix output |
| 6 | Bersama | Tulis test_tambahan.py (12 test regresi + 5 edge case) | Diterima dengan modifikasi — beberapa test disesuaikan nama dan komentar | AI menghasilkan kerangka test, kami menambah komentar penjelasan | Dijalankan `python -m pytest tests/test_tambahan.py -v` — 17/17 passed |
| 7 | Bersama | Lengkapi ground_truth.csv untuk audit.sql dan pemeliharaan.sql | Diubah — verifikasi manual per statement berdasarkan spesifikasi | AI menghasilkan draft awal, kami verifikasi satu per satu | Dijalankan `python evaluate.py` — parser precision/recall 1.00 |
| 8 | Bersama | Tulis laporan bug, kartu desain, laporan akhir | Diterima dengan modifikasi — bagian "akar masalah" ditulis ulang dengan kata sendiri | AI menyediakan kerangka, kami isi dengan pemahaman sendiri | Review silang antar anggota |

**Refleksi (3-5 kalimat).** AI paling membantu di tahap awal: mengidentifikasi bug secara sistematis
dengan membandingkan kode terhadap spesifikasi, yang menghemat waktu eksplorasi. AI juga membantu
menulis kerangka test regresi sehingga kami bisa fokus pada logika verifikasi. Namun AI sempat keliru
dalam urutan fix — menyarankan perbaikan parser sebelum lexer diperbaiki, yang menyebabkan cascading
error. Kami mengetahuinya karena test yang seharusnya lulus masih gagal. Pelajarannya: urutan pipeline
(lexer → parser → resolver → analyzer) harus diikuti juga saat debugging, dan setiap fix harus
diverifikasi secara inkremental dengan test.
