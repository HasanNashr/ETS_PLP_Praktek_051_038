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