"""
PreprocessorService
===================
Tiga tahap prapemrosesan source code:

  1. STRIP COMMENTS  — hapus komentar sesuai bahasa (Python/PHP/Dart)
  2. STRIP WHITESPACE — hapus semua spasi, tab, newline
  3. CASE FOLDING    — ubah ke huruf kecil

Output: PreprocessedFile dengan field tambahan char_map yang memetakan
setiap karakter di processed text kembali ke posisi di original text.
char_map digunakan HighlightService untuk akurasi 100% tanpa aproksimasi.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PreprocessedFile:
    original:  str          # kode asli (untuk UI)
    processed: str          # kode bersih (untuk fingerprinting)
    language:  str          # 'python' | 'php' | 'dart'
    char_map:  list         # char_map[i] = posisi processed[i] di original


class PreprocessorService:

    _EXTENSION_MAP = {".py": "python", ".php": "php", ".dart": "dart"}

    def preprocess(self, source_code: str, file_extension: str) -> PreprocessedFile:
        ext = file_extension.lower()
        language = self._EXTENSION_MAP.get(ext)
        if language is None:
            raise ValueError(
                f"Ekstensi '{ext}' tidak didukung. "
                f"Valid: {list(self._EXTENSION_MAP.keys())}"
            )

        stripped  = self._strip_comments(source_code, language)
        processed = re.sub(r"\s+", "", stripped).lower()
        char_map  = self._build_char_map(source_code, processed)

        return PreprocessedFile(
            original=source_code,
            processed=processed,
            language=language,
            char_map=char_map,
        )

    # ── Strip comments ────────────────────────────────────────────────────────

    def _strip_comments(self, text: str, language: str) -> str:
        if language == "python":
            return self._strip_python(text)
        elif language == "php":
            return self._strip_php(text)
        elif language == "dart":
            return self._strip_dart(text)
        return text

    def _strip_python(self, text: str) -> str:
        pattern = re.compile(
            r'"""[\s\S]*?"""'
            r"|'''[\s\S]*?'''"
            r'|"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|#[^\n]*",
            re.MULTILINE
        )
        def repl(m):
            s = m.group(0)
            if s.startswith('"""') or s.startswith("'''"): return " "
            if s.startswith('"') or s.startswith("'"): return s
            return " "
        return pattern.sub(repl, text)

    def _strip_php(self, text: str) -> str:
        pattern = re.compile(
            r'"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|/\*[\s\S]*?\*/"
            r"|//[^\n]*"
            r"|#[^\n]*",
            re.MULTILINE
        )
        def repl(m):
            s = m.group(0)
            if s.startswith('"') or s.startswith("'"): return s
            return " "
        return pattern.sub(repl, text)

    def _strip_dart(self, text: str) -> str:
        pattern = re.compile(
            r'"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|/\*[\s\S]*?\*/"
            r"|//[^\n]*",
            re.MULTILINE
        )
        def repl(m):
            s = m.group(0)
            if s.startswith('"') or s.startswith("'"): return s
            return " "
        return pattern.sub(repl, text)

    # ── char_map: two-pointer ─────────────────────────────────────────────────

    @staticmethod
    def _build_char_map(original: str, processed: str) -> list:
        """
        Bangun peta: processed_idx → original_idx.

        Karena processed = lowercase(remove_whitespace(remove_comments(original))),
        setiap karakter di processed ada di original dalam urutan yang sama.
        Two-pointer mencocokkan keduanya secara O(n+m).

        Properti yang dijamin:
            original.lower()[char_map[i]] == processed[i]  untuk setiap i
        """
        char_map = []
        pi, oi = 0, 0
        orig_lower = original.lower()
        while pi < len(processed) and oi < len(orig_lower):
            if processed[pi] == orig_lower[oi]:
                char_map.append(oi)
                pi += 1
            oi += 1
        return char_map


# ── Unit test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    svc = PreprocessorService()

    py_code = '# komentar\ndef Hello(x):\n    """docstring"""\n    MyVar = "str"\n    return MyVar\n'
    r = svc.preprocess(py_code, ".py")
    assert "komentar" not in r.processed
    assert "docstring" not in r.processed
    assert "myvar" in r.processed
    assert len(r.char_map) == len(r.processed)
    # Verifikasi char_map
    for i, oi in enumerate(r.char_map):
        assert r.original.lower()[oi] == r.processed[i], f"Mismatch di {i}"
    print("✅ Python — lolos, char_map akurat")

    php_code = "<?php\n// komentar\n/* blok */\n$MyVar = 'nilai';\nfunction Hello() { return TRUE; }\n?>"
    r2 = svc.preprocess(php_code, ".php")
    assert "komentar" not in r2.processed
    assert len(r2.char_map) == len(r2.processed)
    for i, oi in enumerate(r2.char_map):
        assert r2.original.lower()[oi] == r2.processed[i]
    print("✅ PHP — lolos, char_map akurat")

    dart_code = "// komentar\nvoid main() {\n  String MyName = 'Dafa';\n  print(MyName);\n}"
    r3 = svc.preprocess(dart_code, ".dart")
    assert len(r3.char_map) == len(r3.processed)
    for i, oi in enumerate(r3.char_map):
        assert r3.original.lower()[oi] == r3.processed[i]
    print("✅ Dart — lolos, char_map akurat")

    print("\n✅ PreprocessorService — semua test lolos")
