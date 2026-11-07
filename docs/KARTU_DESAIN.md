# Kartu Desain

Tuliskan lima keputusan desain penting dalam pekerjaan kalian. Untuk tiap keputusan, sebutkan
alternatif yang ditolak dan alasannya. Contoh topik (boleh memilih yang lain):

- bagaimana parser membedakan `*` sebagai "semua kolom" dan sebagai perkalian;
- di mana dan bagaimana presedensi `AND`/`OR` dinyatakan;
- mengapa error recovery berhenti di `;`, bukan di keyword `SELECT` berikutnya;
- urutan pencarian scope dan akibatnya pada shadowing serta correlated subquery;
- mengapa kolom tanpa qualifier hanya dilihat di scope terdalam, dan apa kelemahannya;
- bagaimana implementasi `INSERT ... SELECT` atau komentar blok kalian.

| No | Keputusan | Alternatif yang ditolak | Alasan |
| --- | --- | --- | --- |
| 1 | **Presedensi AND/OR dipisah jadi dua fungsi (`_or()` dan `_and()`)** dalam recursive descent parser, masing-masing memanggil level di bawahnya. `_or()` memanggil `_and()`, `_and()` memanggil `_not()`. | (a) Menangani AND/OR dalam satu fungsi dengan tabel precedence; (b) Pratt parsing untuk seluruh ekspresi. | Satu fungsi per level lebih mudah dibaca, di-debug, dan sesuai pola Crafting Interpreters bab 6. Pratt parsing mengubah arsitektur terlalu drastis dan tidak sesuai kode awal yang sudah recursive descent. |
| 2 | **Error recovery berhenti di `;`** (`_synchronize()` membuang token sampai dan termasuk SEMICOLON, lalu parsing dilanjutkan). | (a) Berhenti di keyword awal statement (SELECT, INSERT, dll.); (b) Berhenti di EOF dan melaporkan semua error sekaligus. | Spesifikasi §6 secara eksplisit menyatakan "buang token sampai dan termasuk `;`". Berhenti di keyword bisa menelan keyword yang seharusnya menjadi bagian ekspresi (seperti `IN`, `EXISTS`). Berhenti di EOF berarti kehilangan semua statement valid setelah error. |
| 3 | **Komentar blok diimplementasi di lexer dengan loop sederhana** yang mencari `*/` sebagai penutup, tanpa mendukung komentar bersarang. | (a) Mendukung komentar bersarang dengan counter depth; (b) Menggunakan regex untuk mencocokkan komentar blok. | Spesifikasi §2.3 menyatakan komentar blok "tidak bersarang", jadi counter depth tidak diperlukan. Regex sulit menangani komentar lintas baris dan tidak sesuai arsitektur lexer karakter-per-karakter. Loop sederhana lebih jelas dan mudah diverifikasi. |
| 4 | **Pencarian scope dari terdalam ke luar** untuk qualified column (`_lookup()` iterasi dari `self.scope` ke `scope.parent`). Ini memungkinkan shadowing dan correlated subquery. | (a) Hanya mencari di scope terdalam; (b) Mencari dari scope terluar ke dalam. | Spesifikasi §4.3 mengatakan "qualifier dicari mulai dari scope terdalam ke luar". Pencarian terluar-dulu akan memecah shadowing — alias subquery tidak bisa menutupi alias luar. Pencarian hanya scope terdalam akan memecah correlated subquery yang merujuk alias luar. |
| 5 | **INSERT...SELECT diimplementasi dengan memanggil `_select()` yang sudah ada** dan menyimpan hasilnya di field `query` dari node `Insert`. Field `values` diset ke list kosong `[]`. | (a) Membuat node AST baru khusus `InsertSelect`; (b) Mem-parse SELECT secara inline tanpa reuse. | Reuse `_select()` mengikuti prinsip DRY dan tidak mengubah API publik (node `Insert` sudah punya field `query`). Node baru membutuhkan perubahan di resolver, analyzer, dan pipeline. Parse inline duplikatif dan rawan bug. |
