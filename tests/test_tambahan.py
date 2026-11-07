"""Test tambahan buatan kelompok.

Isi dengan:
1. Satu test regresi untuk setiap bug yang kalian perbaiki (gagal sebelum perbaikan,
   lulus sesudahnya). Beri nama yang menjelaskan bug-nya.
2. Lima test kasus tepi, masing-masing dengan komentar singkat mengapa kasus itu berisiko.
"""
import pytest

from crud.lexer import LexError, TokenType as T, tokenize
from crud import ast_nodes as ast
from crud.parser import parse_sql, ParseError
from crud.resolver import Resolver
from crud.analyzer import analyze_statement
from crud.pipeline import analyze_source


# === Helper ===
def one(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    assert len(script.statements) == 1
    return script.statements[0]


def resolve(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    diags = Resolver().resolve_script(script)
    return script, diags


def columns(node):
    return [n for n in ast.iter_nodes(node) if isinstance(n, ast.ColumnRef)]


def crud(sql):
    script = parse_sql(sql)
    assert script.errors == [], script.errors
    return analyze_statement(script.statements[0])


# =====================================================================
# BAGIAN 1: TEST REGRESI PER BUG
# =====================================================================

# --- Bug B1: Lexer _word() tidak case-insensitive ---
# Sebelum fix: keyword huruf kecil/campuran menjadi IDENT, bukan KEYWORD.
# Spesifikasi §2.2: keyword tidak peka huruf besar/kecil.
def test_regresi_b1_keyword_case_insensitive():
    toks = tokenize("select FROM Update DeLeTe")
    kw_toks = [t for t in toks if t.type == T.KEYWORD]
    assert [t.value for t in kw_toks] == ["SELECT", "FROM", "UPDATE", "DELETE"]

# --- Bug B2: Lexer _string() tidak menangani escaped quote '' ---
# Sebelum fix: 'O''Brien' menghasilkan dua token terpisah.
# Spesifikasi §2.4: '' di dalam string mewakili satu karakter kutip.
def test_regresi_b2_escaped_quote_dalam_string():
    toks = tokenize("'O''Brien'")
    assert toks[0].type == T.STRING
    assert toks[0].value == "O'Brien"


# --- Bug B3: Lexer tidak mengenali operator <> (maximal munch) ---
# Sebelum fix: <> menjadi dua token < dan >, bukan satu token <>.
# Spesifikasi §2.5: maximal munch, <> adalah satu token.
def test_regresi_b3_operator_not_equal():
    toks = tokenize("a <> b")
    ops = [t for t in toks if t.type == T.OP]
    assert len(ops) == 1
    assert ops[0].value == "<>"


# --- Bug B4: Parser AND/OR di level precedence yang sama ---
# Sebelum fix: a = 1 OR b = 2 AND c = 3 diparsing sebagai (a=1 OR b=2) AND c=3.
# Spesifikasi §3.1: AND memiliki precedence lebih tinggi dari OR.
def test_regresi_b4_precedence_and_or():
    s = one("SELECT id FROM t WHERE a = 1 OR b = 2 AND c = 3")
    # Harus: a=1 OR (b=2 AND c=3)
    assert s.where.op == "OR"
    assert s.where.right.op == "AND"


# --- Bug B5: Parser _synchronize() membuang semua token sampai EOF ---
# Sebelum fix: setelah error, SEMUA statement berikutnya hilang.
# Spesifikasi §6: error recovery buang sampai ';', lalu lanjutkan.
def test_regresi_b5_error_recovery_lanjut_setelah_semicolon():
    script = parse_sql("SELECT FROM ; SELECT id FROM t;")
    # Statement pertama error, tapi yang kedua harus berhasil diparse
    assert len(script.errors) == 1
    assert len(script.statements) == 1
    assert isinstance(script.statements[0], ast.Select)


# --- Bug B6: Parser _join() tidak menangani LEFT OUTER JOIN ---
# Sebelum fix: LEFT OUTER JOIN gagal karena OUTER tidak dikonsumsi.
# Spesifikasi §3 grammar: join = [ ... | "LEFT" [ "OUTER" ] ] "JOIN" ...
def test_regresi_b6_left_outer_join():
    s = one("SELECT a.id FROM a LEFT OUTER JOIN b ON b.a_id = a.id")
    assert s.joins[0].kind == "LEFT"
    assert s.joins[0].source.name == "b"


# --- Bug B7: Resolver _delete() tidak memanggil _pop() ---
# Sebelum fix: scope bocor, alias dari DELETE terlihat oleh statement berikutnya.
# Spesifikasi §4.5: setiap statement berdiri sendiri, tidak ada scope tersisa.
def test_regresi_b7_delete_scope_bocor():
    script, diags = resolve(
        "DELETE FROM sesi s WHERE s.id = 1;"
        "SELECT p.nama FROM pelanggan p"
    )
    # Alias 's' dari DELETE tidak boleh terlihat di SELECT berikutnya
    errors = [d for d in diags if d.level == "error"]
    assert errors == []


# --- Bug B8: Resolver _lookup() urutan pencarian terbalik ---
# Sebelum fix: pencarian scope dari luar ke dalam, sehingga shadowing tidak bekerja.
# Spesifikasi §4.3: pencarian dari scope terdalam ke luar.
def test_regresi_b8_shadowing_subquery():
    script, diags = resolve(
        "SELECT x.id FROM pelanggan x "
        "WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x WHERE x.total > 500000)"
    )
    # x di subquery harus resolve ke pesanan (shadowing), bukan pelanggan
    inner_cols = [c for c in columns(script) if c.qualifier == "x" and c.name == "total"]
    assert len(inner_cols) == 1
    assert inner_cols[0].resolved == "pesanan"


# --- Bug B9: Analyzer UPDATE subquery diberi op "U" alih-alih "R" ---
# Sebelum fix: tabel di subquery WHERE/SET pada UPDATE ditandai "U".
# Spesifikasi §5: subquery selalu R.
def test_regresi_b9_update_subquery_operasi_read():
    result = crud(
        "UPDATE pelanggan SET level = 'gold' "
        "WHERE id IN (SELECT pelanggan_id FROM pesanan WHERE total > 1000000)"
    )
    assert result["pelanggan"] == {"U"}
    assert result["pesanan"] == {"R"}


# --- TODO T1: INSERT INTO ... SELECT ---
def test_regresi_t1_insert_select():
    s = one("INSERT INTO arsip (id, total) SELECT id, total FROM pesanan WHERE tanggal < :batas")
    assert isinstance(s, ast.Insert)
    assert s.columns == ["id", "total"]
    assert isinstance(s.query, ast.Select)
    assert s.query.sources[0].name == "pesanan"


# --- TODO T2: Kolom tanpa qualifier di-resolve ---
def test_regresi_t2_kolom_tanpa_qualifier():
    script, diags = resolve("SELECT nama, aktif FROM pelanggan WHERE id = 1")
    cols = columns(script)
    assert all(c.resolved == "pelanggan" for c in cols)
    assert diags == []


# --- TODO T3: Komentar blok /* ... */ ---
def test_regresi_t3_komentar_blok():
    toks = tokenize("/* komentar\n   multi baris */ SELECT id")
    assert toks[0].type == T.KEYWORD
    assert toks[0].value == "SELECT"
    assert toks[0].line == 2


# =====================================================================
# BAGIAN 2: LIMA TEST KASUS TEPI
# =====================================================================

# Kasus tepi 1: Komentar blok yang mengandung '*' di dalamnya.
# Berisiko karena '*' bisa salah dibaca sebagai awal dari '*/' penutup.
def test_edge_komentar_blok_dengan_bintang():
    toks = tokenize("/* harga * qty */ SELECT id FROM t")
    non_eof = [t for t in toks if t.type != T.EOF]
    assert non_eof[0].value == "SELECT"


# Kasus tepi 2: Komentar blok yang tidak ditutup harus error.
# Berisiko karena tanpa validasi, lexer bisa loop tak terbatas.
def test_edge_komentar_blok_tidak_ditutup():
    with pytest.raises(LexError) as info:
        tokenize("/* komentar tanpa tutup")
    assert "tidak ditutup" in str(info.value)


# Kasus tepi 3: String dengan banyak escaped quote berturut-turut.
# Berisiko karena '' harus dibedakan dari ' penutup.
def test_edge_string_multi_escape():
    toks = tokenize("'a''''b'")
    # a + '' + '' + b = a''b
    assert toks[0].type == T.STRING
    assert toks[0].value == "a''b"


# Kasus tepi 4: BETWEEN ... AND ... di dalam AND logika.
# Berisiko karena AND milik BETWEEN harus dibedakan dari AND logika.
def test_edge_between_and_logika():
    s = one("SELECT id FROM t WHERE x BETWEEN 1 AND 10 AND y = 5")
    # Harus: (x BETWEEN 1 AND 10) AND (y = 5)
    assert isinstance(s.where, ast.BinaryOp) and s.where.op == "AND"
    assert isinstance(s.where.left, ast.Between)
    assert isinstance(s.where.right, ast.BinaryOp) and s.where.right.op == "="


# Kasus tepi 5: Kolom tanpa qualifier dengan beberapa tabel → ambigu.
# Berisiko karena resolver harus memilih warning, bukan crash.
def test_edge_kolom_ambigu_multi_tabel():
    script, diags = resolve("SELECT nama FROM pelanggan, pesanan WHERE aktif = 1")
    warnings = [d for d in diags if d.level == "warning"]
    assert any("ambigu" in w.message for w in warnings)
    # resolved harus None karena ambigu
    cols = columns(script)
    assert all(c.resolved is None for c in cols)
