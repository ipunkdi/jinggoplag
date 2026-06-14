"""
HighlightService
================
Mengubah matched_hashes → nomor baris di original_text
untuk di-render sebagai highlight kuning di halaman Detail.

Pipeline:
    matched_hashes (set[int])
        ↓
    filter hash_positions → matched char ranges
        ↓
    char ranges → set nomor baris
        ↓
    list[HighlightedLine] — satu entri per baris
"""

from dataclasses import dataclass


@dataclass
class HighlightedLine:
    """Representasi satu baris kode untuk UI Detail."""

    line_number: int   # 1-indexed
    content:     str   # teks baris asli (tidak dimodifikasi)
    is_match:    bool  # True → sorot kuning, False → tampil normal


class HighlightService:
    """Memetakan matched fingerprint hashes ke nomor baris di source code asli."""

    def highlight(
        self,
        original_text:  str,
        hash_positions: list,
        matched_hashes: set,
    ) -> list:
        """
        Hasilkan list baris dengan informasi is_match.

        Args:
            original_text:  Kode sumber asli (dengan newline).
            hash_positions: Output FingerprintResult.hash_positions
                            → [(hash_value, char_start, char_end), ...].
            matched_hashes: Output FilePairResult.matched_hashes (set[int]).

        Returns:
            list[HighlightedLine] — satu entri per baris, berurutan atas ke bawah.
        """
        matched_ranges   = self._get_matched_ranges(hash_positions, matched_hashes)
        char_to_line_map = self._build_char_to_line_map(original_text)
        matched_lines    = self._ranges_to_lines(
            matched_ranges, char_to_line_map, len(original_text)
        )

        lines = original_text.splitlines()
        if not lines:
            return [HighlightedLine(line_number=1, content="", is_match=False)]

        return [
            HighlightedLine(
                line_number=idx + 1,
                content=line,
                is_match=(idx + 1 in matched_lines),
            )
            for idx, line in enumerate(lines)
        ]

    # ── Step 1: filter matched ranges ─────────────────────────────────────────

    @staticmethod
    def _get_matched_ranges(hash_positions: list, matched_hashes: set) -> list:
        """Ekstrak char ranges hanya untuk hash yang ada di matched_hashes."""
        return [
            (char_start, char_end)
            for hash_val, char_start, char_end in hash_positions
            if hash_val in matched_hashes
        ]

    # ── Step 2: char index → line number map ──────────────────────────────────

    @staticmethod
    def _build_char_to_line_map(text: str) -> list:
        """
        Bangun array: indeks = posisi karakter, nilai = nomor baris (1-indexed).

        Contoh untuk "ab\\ncd":
            char 0 ('a') → baris 1
            char 2 ('\\n') → baris 1
            char 3 ('c') → baris 2
        """
        char_to_line: list = []
        current_line = 1

        for char in text:
            char_to_line.append(current_line)
            if char == "\n":
                current_line += 1

        char_to_line.append(current_line)  # ekstra untuk boundary safety
        return char_to_line

    # ── Step 3: char ranges → line number set ─────────────────────────────────

    def _ranges_to_lines(
        self,
        char_ranges: list,
        char_to_line: list,
        text_len: int,
    ) -> set:
        """Konversi list (char_start, char_end) → set nomor baris yang di-cover."""
        matched: set = set()
        map_len = len(char_to_line)

        for char_start, char_end in char_ranges:
            clamped_start = max(0, min(char_start, text_len - 1))
            clamped_end   = max(clamped_start, min(char_end, text_len))

            start_line = char_to_line[clamped_start] if clamped_start < map_len else 1
            end_idx    = clamped_end - 1
            end_line   = char_to_line[end_idx] if end_idx < map_len else start_line

            for line_num in range(start_line, end_line + 1):
                matched.add(line_num)

        return matched

    # ── Utilitas ──────────────────────────────────────────────────────────────

    @staticmethod
    def compute_match_stats(highlighted_lines: list) -> dict:
        """
        Hitung statistik highlight untuk ditampilkan di UI.

        Returns:
            Dict dengan total_lines, matched_lines, dan match_ratio (0.0–100.0).
        """
        total   = len(highlighted_lines)
        matched = sum(1 for ln in highlighted_lines if ln.is_match)
        ratio   = (matched / total * 100.0) if total > 0 else 0.0
        return {
            "total_lines":   total,
            "matched_lines": matched,
            "match_ratio":   round(ratio, 2),
        }
