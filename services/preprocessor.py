"""
PreprocessorService
===================
Tiga tahap prapemrosesan source code:

  1. STRIP COMMENTS   — hapus komentar sesuai bahasa (Python/PHP/Dart)
  2. STRIP WHITESPACE — hapus semua spasi, tab, newline
  3. CASE FOLDING     — ubah ke huruf kecil

Output: PreprocessedFile dengan field char_map yang memetakan setiap
karakter di processed text kembali ke posisi tepat di original text.
char_map digunakan HighlightService untuk akurasi 100%.
"""

import re
from dataclasses import dataclass


@dataclass
class PreprocessedFile:
    """Container hasil preprocessing satu file source code."""

    original:  str   # kode asli — digunakan UI
    processed: str   # kode bersih — input FingerprintService
    language:  str   # 'python' | 'php' | 'dart'
    char_map:  list  # char_map[i] = posisi processed[i] di original


class PreprocessorService:
    """Melakukan prapemrosesan source code secara bahasa-spesifik."""

    _EXTENSION_MAP: dict = {
        ".py":   "python",
        ".php":  "php",
        ".dart": "dart",
    }

    def preprocess(self, source_code: str, file_extension: str) -> PreprocessedFile:
        """
        Jalankan pipeline preprocessing: strip komentar → strip whitespace → lowercase.

        Args:
            source_code:    Kode sumber mentah.
            file_extension: Ekstensi file, mis. '.py', '.php', '.dart'.

        Returns:
            PreprocessedFile berisi original, processed, language, char_map.

        Raises:
            ValueError: Jika ekstensi tidak didukung.
        """
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
        """Hapus komentar sesuai bahasa."""
        if language == "python":
            return self._strip_python(text)
        if language == "php":
            return self._strip_php(text)
        if language == "dart":
            return self._strip_dart(text)
        return text

    def _strip_python(self, text: str) -> str:
        """
        Hapus komentar Python: docstring triple-quote dan komentar # inline.
        String literal dipertahankan agar '#' di dalam string tidak ikut dihapus.
        """
        pattern = re.compile(
            r'"""[\s\S]*?"""'
            r"|'''[\s\S]*?'''"
            r'|"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|#[^\n]*",
            re.MULTILINE,
        )

        def _replace(match: re.Match) -> str:
            token = match.group(0)
            if token.startswith('"""') or token.startswith("'''"):
                return " "
            if token.startswith('"') or token.startswith("'"):
                return token
            return " "

        return pattern.sub(_replace, text)

    def _strip_php(self, text: str) -> str:
        """Hapus komentar PHP: //, #, /* ... */. String literal dipertahankan."""
        pattern = re.compile(
            r'"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|/\*[\s\S]*?\*/"
            r"|//[^\n]*"
            r"|#[^\n]*",
            re.MULTILINE,
        )

        def _replace(match: re.Match) -> str:
            token = match.group(0)
            if token.startswith('"') or token.startswith("'"):
                return token
            return " "

        return pattern.sub(_replace, text)

    def _strip_dart(self, text: str) -> str:
        """Hapus komentar Dart: // dan /* ... */. String literal dipertahankan."""
        pattern = re.compile(
            r'"(?:\\.|[^"\\])*"'
            r"|'(?:\\.|[^'\\])*'"
            r"|/\*[\s\S]*?\*/"
            r"|//[^\n]*",
            re.MULTILINE,
        )

        def _replace(match: re.Match) -> str:
            token = match.group(0)
            if token.startswith('"') or token.startswith("'"):
                return token
            return " "

        return pattern.sub(_replace, text)

    # ── char_map: two-pointer ─────────────────────────────────────────────────

    @staticmethod
    def _build_char_map(original: str, processed: str) -> list:
        """
        Bangun peta processed_idx → original_idx menggunakan two-pointer O(n+m).

        Karena processed = lowercase(strip_ws(strip_comments(original))),
        setiap karakter di processed ada di original dalam urutan yang sama.

        Properti yang dijamin:
            original.lower()[char_map[i]] == processed[i]  untuk setiap i.
        """
        char_map: list = []
        proc_idx  = 0
        orig_idx  = 0
        orig_lower = original.lower()

        while proc_idx < len(processed) and orig_idx < len(orig_lower):
            if processed[proc_idx] == orig_lower[orig_idx]:
                char_map.append(orig_idx)
                proc_idx += 1
            orig_idx += 1

        return char_map
