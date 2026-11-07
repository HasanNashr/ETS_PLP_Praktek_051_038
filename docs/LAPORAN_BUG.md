# Laporan Bug

Salin blok di bawah untuk setiap bug. Bagian **Akar masalah** wajib ditulis dengan kata-kata
sendiri dan memakai konsep dari *Crafting Interpreters* (sebutkan bab). Bagian ini diuji lisan.

---

## Bug 1: Lexer tidak mengenali keyword huruf kecil/campuran

**Ditemukan oleh:** Hasan Nashrullah · **Diperbaiki oleh:** Hasan Nashrullah

**Gejala.** Input `select id from t` menghasilkan token `IDENT('select')` dan `IDENT('from')`, bukan `KEYWORD('SELECT')` dan `KEYWORD('FROM')`. Akibatnya parser gagal mengenali statement. Menurut SPESIFIKASI.md bagian 2.2, keyword tidak peka huruf besar/kecil dan selalu dinormalisasi ke huruf besar.

**Reproduksi minimal.**

```sql
select id from t
```

**Akar masalah.** Pada fungsi `_word()` di `crud/lexer.py`, pengecekan dilakukan dengan `text in KEYWORDS` tanpa menormalisasi `text` ke huruf besar terlebih dahulu. Karena set `KEYWORDS` hanya berisi huruf besar (`"SELECT"`, `"FROM"`, dll.), kata `"select"` tidak cocok dan diklasifikasikan sebagai `IDENT`. Ini melanggar prinsip *scanning* di Crafting Interpreters bab 4: scanner harus mengenali *reserved words* terlepas dari casing-nya.

**Perbaikan.** Di `crud/lexer.py`, fungsi `_word()`: tambahkan `upper = text.upper()` sebelum pengecekan, lalu gunakan `upper in KEYWORDS` dan simpan nilai token sebagai `upper`. Alternatif yang dipertimbangkan: mengubah `KEYWORDS` menjadi lowercase — ditolak karena spesifikasi mewajibkan nilai token keyword selalu huruf besar.

**Test regresi.** `test_regresi_b1_keyword_case_insensitive` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini dengan membandingkan kode dengan spesifikasi. Diverifikasi dengan menjalankan `tokenize("select FROM Update DeLeTe")` dan memastikan semua menjadi `KEYWORD`.

---

## Bug 2: Lexer tidak menangani escaped quote '' dalam string

**Ditemukan oleh:** Hasan Nashrullah · **Diperbaiki oleh:** Hasan Nashrullah

**Gejala.** Input `'O''Brien'` seharusnya menghasilkan satu token `STRING` dengan nilai `O'Brien`, tetapi lexer berhenti pada kutip kedua dan menghasilkan `STRING('O')` diikuti token lain. Menurut SPESIFIKASI.md bagian 2.4, dua kutip berturut-turut (`''`) mewakili satu karakter kutip.

**Reproduksi minimal.**

```sql
'O''Brien'
```

**Akar masalah.** Pada fungsi `_string()`, saat menemukan karakter `'`, kode langsung `break` tanpa memeriksa apakah karakter berikutnya juga `'`. Ini melanggar aturan *lexical grammar* untuk *string escape* (Crafting Interpreters bab 4): scanner harus memeriksa apakah kutip adalah *escape sequence* (`''`) atau penutup string.

**Perbaikan.** Di `crud/lexer.py`, fungsi `_string()`: setelah menemukan `'`, periksa `self._peek() == "'"`. Jika iya, konsumsi kutip kedua dan tambahkan `'` ke buffer. Jika tidak, baru `break`. Alternatif: menggunakan backslash escape (`\'`) — ditolak karena tidak sesuai standar SQL.

**Test regresi.** `test_regresi_b2_escaped_quote_dalam_string` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini. Diverifikasi dengan file `pemeliharaan.sql` yang mengandung `'O''Brien'` dan `'O''Neil'`.

---

## Bug 3: Lexer tidak mengenali operator `<>` (maximal munch)

**Ditemukan oleh:** Hasan Nashrullah · **Diperbaiki oleh:** Hasan Nashrullah

**Gejala.** Input `a <> b` menghasilkan dua token `OP('<')` dan `OP('>')` alih-alih satu token `OP('<>')`. Akibatnya parser gagal mem-parse ekspresi perbandingan dengan `<>`. Menurut SPESIFIKASI.md bagian 2.5, lexer selalu mengambil operator terpanjang yang cocok (maximal munch).

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE status <> 'aktif'
```

**Akar masalah.** Pada handler `ch == "<"` di `_scan_token()`, kode hanya memeriksa `self._match("=")` untuk `<=`, tetapi tidak memeriksa `self._match(">")` untuk `<>`. Ini melanggar prinsip *maximal munch* (Crafting Interpreters bab 4): scanner harus selalu memilih token terpanjang.

**Perbaikan.** Di `crud/lexer.py`, fungsi `_scan_token()` pada handler `<`: tambahkan `elif self._match(">")` yang menghasilkan `<>`. Alternatif: memperlakukan `<>` sebagai dua token terpisah di parser — ditolak karena melanggar spesifikasi lexer.

**Test regresi.** `test_regresi_b3_operator_not_equal` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini dari kegagalan test `laporan_penjualan.sql` yang menggunakan `<>`. Diverifikasi dengan tokenize `"a <> b"`.

---

## Bug 4: Parser AND dan OR di level precedence yang sama

**Ditemukan oleh:** Amor Azzam Imani · **Diperbaiki oleh:** Amor Azzam Imani

**Gejala.** Input `a = 1 OR b = 2 AND c = 3` diparsing sebagai `(a=1 OR b=2) AND c=3`, padahal menurut SPESIFIKASI.md bagian 3.1, AND memiliki precedence lebih tinggi (level 2) daripada OR (level 1), sehingga seharusnya `a=1 OR (b=2 AND c=3)`.

**Reproduksi minimal.**

```sql
SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3
```

**Akar masalah.** Fungsi `_logical()` menangani OR dan AND dalam satu loop (`while self._check_kw("AND", "OR")`). Karena keduanya di level yang sama, ekspresi di-parse secara left-associative tanpa membedakan precedence. Menurut Crafting Interpreters bab 6, setiap level precedence harus ditangani oleh fungsi terpisah dalam recursive descent parser.

**Perbaikan.** Di `crud/parser.py`: pecah `_logical()` menjadi `_or()` dan `_and()`, di mana `_or()` memanggil `_and()` sebagai operand. Ini memastikan AND di-evaluasi lebih dulu. Alternatif: Pratt parsing — ditolak karena mengubah arsitektur terlalu banyak.

**Test regresi.** `test_regresi_b4_precedence_and_or` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi pola bug ini. Diverifikasi dengan membandingkan AST output pada `audit.sql` baris 6.

---

## Bug 5: Parser error recovery membuang semua token sampai EOF

**Ditemukan oleh:** Hasan Nashrullah · **Diperbaiki oleh:** Hasan Nashrullah

**Gejala.** Jika ada satu statement yang error, semua statement setelahnya juga hilang. Misalnya pada `campuran_error.sql`, seharusnya hanya baris 4 yang error, tetapi baris 6 dan 8 juga tidak diparse. Menurut SPESIFIKASI.md bagian 6, error recovery harus buang token sampai dan termasuk `;`, lalu lanjutkan.

**Reproduksi minimal.**

```sql
SELECT FROM ; SELECT id FROM t;
```

**Akar masalah.** Fungsi `_synchronize()` berisi `while not self._at_end(): self._advance()` yang membuang SEMUA sisa token tanpa berhenti di `;`. Ini melanggar *panic mode recovery* (Crafting Interpreters bab 6): synchronization point harusnya di `;` sebagai batas statement.

**Perbaikan.** Di `crud/parser.py`, fungsi `_synchronize()`: ubah agar berhenti setelah menemukan `SEMICOLON` — `if tok.type == T.SEMICOLON: return`. Alternatif: berhenti di keyword awal statement — ditolak karena spesifikasi secara eksplisit menyebut `;`.

**Test regresi.** `test_regresi_b5_error_recovery_lanjut_setelah_semicolon` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini. Diverifikasi dengan `campuran_error.sql` yang kini menunjukkan 3 statement valid + 1 error.

---

## Bug 6: Parser tidak menangani LEFT OUTER JOIN

**Ditemukan oleh:** Hasan Nashrullah · **Diperbaiki oleh:** Hasan Nashrullah

**Gejala.** Input `LEFT OUTER JOIN` gagal diparse karena setelah mengkonsumsi `LEFT`, parser langsung mengharapkan `JOIN`, tetapi menemukan `OUTER`. Menurut SPESIFIKASI.md bagian 3 grammar: `join = [ ... | "LEFT" [ "OUTER" ] ] "JOIN" ...`.

**Reproduksi minimal.**

```sql
SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id
```

**Akar masalah.** Pada fungsi `_join()`, setelah `self._match_kw("LEFT")`, kode tidak mencoba mengkonsumsi keyword opsional `OUTER`. Menurut Crafting Interpreters bab 6, untuk aturan grammar yang memiliki bagian opsional (seperti `[ "OUTER" ]`), parser harus mencoba match tanpa memaksa.

**Perbaikan.** Di `crud/parser.py`, fungsi `_join()`: tambahkan `self._match_kw("OUTER")` setelah berhasil match `LEFT`. Alternatif: mengabaikan semua keyword sebelum JOIN — ditolak karena bisa menelan keyword penting.

**Test regresi.** `test_regresi_b6_left_outer_join` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini dari file `pemeliharaan.sql` baris 5. Diverifikasi dengan `--ast`.

---

## Bug 7: Resolver _delete() tidak memanggil _pop()

**Ditemukan oleh:** Amor Azzam Imani · **Diperbaiki oleh:** Amor Azzam Imani

**Gejala.** Setelah DELETE statement, alias-nya masih terlihat oleh statement berikutnya. Misalnya `DELETE FROM sesi s; SELECT p.nama FROM pelanggan p` — alias `s` masih ada di scope saat SELECT diparse. Menurut SPESIFIKASI.md bagian 4.5, setiap statement berdiri sendiri.

**Reproduksi minimal.**

```sql
DELETE FROM sesi s WHERE s.id = 1; SELECT nama FROM pelanggan
```

**Akar masalah.** Fungsi `_delete()` memanggil `self._push()` untuk membuat scope baru tetapi tidak memanggil `self._pop()` di akhir. Ini menyebabkan scope "bocor". Menurut Crafting Interpreters bab 11, setiap scope yang di-push harus di-pop saat keluar dari konteks yang membuat scope itu.

**Perbaikan.** Di `crud/resolver.py`, fungsi `_delete()`: tambahkan `self._pop()` di akhir fungsi. Alternatif: menggunakan context manager — ditolak karena mengubah API terlalu banyak.

**Test regresi.** `test_regresi_b7_delete_scope_bocor` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini dengan membandingkan `_update()` (yang punya `_pop()`) dengan `_delete()` (yang tidak). Diverifikasi dengan multi-statement SQL.

---

## Bug 8: Resolver _lookup() urutan pencarian scope terbalik

**Ditemukan oleh:** Amor Azzam Imani · **Diperbaiki oleh:** Amor Azzam Imani

**Gejala.** Pada `audit.sql` baris 12-14, alias `x` dipakai di scope luar (pelanggan) dan dalam (pesanan). Kolom `x.pelanggan_id` di subquery seharusnya resolve ke `pesanan` (shadowing), tetapi resolve ke `pelanggan`. Menurut SPESIFIKASI.md bagian 4.3, pencarian scope dari terdalam ke luar.

**Reproduksi minimal.**

```sql
SELECT x.id FROM pelanggan x WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x)
```

**Akar masalah.** Fungsi `_lookup()` membangun list scope dari dalam ke luar (`chain`), lalu iterasi dengan `reversed(chain)` — artinya pencarian dimulai dari scope **terluar**. Ini kebalikan dari spesifikasi. Menurut Crafting Interpreters bab 11, *environment lookup* harus mulai dari scope terdalam agar *shadowing* bekerja.

**Perbaikan.** Di `crud/resolver.py`, fungsi `_lookup()`: sederhanakan menjadi iterasi langsung dari `self.scope` ke `scope.parent` tanpa membalik. Alternatif: tetap pakai chain tapi tanpa reversed — ditolak karena lebih kompleks tanpa keuntungan.

**Test regresi.** `test_regresi_b8_shadowing_subquery` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi pola terbalik ini. Diverifikasi dengan `audit.sql` dan `--ast`.

---

## Bug 9: Analyzer memberikan operasi "U" ke subquery dalam UPDATE

**Ditemukan oleh:** Amor Azzam Imani · **Diperbaiki oleh:** Amor Azzam Imani

**Gejala.** Pada `UPDATE pelanggan SET level = 'gold' WHERE id IN (SELECT pelanggan_id FROM pesanan)`, tabel `pesanan` ditandai `U` (update), padahal seharusnya `R` (read). Menurut SPESIFIKASI.md bagian 5, tabel di subquery UPDATE (di SET maupun WHERE) selalu R.

**Reproduksi minimal.**

```sql
UPDATE pelanggan SET level = 'gold' WHERE id IN (SELECT pelanggan_id FROM pesanan)
```

**Akar masalah.** Pada fungsi `analyze_statement()`, blok `isinstance(stmt, ast.Update)` memanggil `_collect(assignment.value, usage, "U")` dan `_collect(stmt.where, usage, "U")`. Operasi `"U"` diteruskan ke subquery, sehingga tabel di dalam subquery juga ditandai `U`. Seharusnya `"R"` karena subquery hanya membaca data.

**Perbaikan.** Di `crud/analyzer.py`, fungsi `analyze_statement()`: ubah parameter operasi dari `"U"` menjadi `"R"` pada kedua pemanggilan `_collect()` di blok UPDATE. Alternatif: menambah logika khusus di `_collect_select` untuk mengoverride — ditolak karena lebih rumit.

**Test regresi.** `test_regresi_b9_update_subquery_operasi_read` di `tests/test_tambahan.py`

**Peran AI.** AI membantu mengidentifikasi bug ini. Diverifikasi dengan membandingkan output CRUD matrix sebelum dan sesudah fix.

---
