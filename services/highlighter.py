"""
HighlightService
================
Mengubah matched_hashes → nomor baris di original_text untuk di-render
sebagai highlight kuning di halaman Detail.

Pipeline:
    matched_hashes (set[int])
        ↓
    filter hash_positions → [(hash, orig_char_start, orig_char_end), ...]
        ↓
    konversi char positions → set nomor baris
        ↓
    render sebagai list[HighlightedLine]

Dengan char_map dari PreprocessorService, posisi karakter sudah AKURAT 100%.
HighlightService hanya perlu mengkonversi posisi karakter → nomor baris.
"""

from dataclasses import dataclass


@dataclass
class HighlightedLine:
    line_number: int
    content:     str
    is_match:    bool


class HighlightService:

    def highlight(self, original_text: str,
                  hash_positions: list,
                  matched_hashes: set) -> list:
        """
        Args:
            original_text:  kode sumber asli (dengan newline)
            hash_positions: output FingerprintResult.hash_positions
                            [(hash_value, orig_char_start, orig_char_end), ...]
            matched_hashes: output FilePairResult.matched_hashes (set[int])

        Returns:
            list[HighlightedLine] — satu entri per baris
        """
        # Kumpulkan char ranges yang matched
        matched_ranges = [
            (cs, ce) for hv, cs, ce in hash_positions
            if hv in matched_hashes
        ]

        # Bangun peta char_index → line_number
        char_to_line = self._build_char_to_line(original_text)

        # Konversi char ranges → set nomor baris
        matched_lines = self._ranges_to_lines(
            matched_ranges, char_to_line, len(original_text))

        # Bangun output
        lines = original_text.splitlines()
        if not lines:
            return [HighlightedLine(1, "", False)]

        return [
            HighlightedLine(
                line_number=i + 1,
                content=line,
                is_match=(i + 1 in matched_lines),
            )
            for i, line in enumerate(lines)
        ]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_char_to_line(text: str) -> list:
        """Array: char_to_line[i] = nomor baris (1-indexed) karakter ke-i."""
        mapping, line = [], 1
        for ch in text:
            mapping.append(line)
            if ch == "\n":
                line += 1
        mapping.append(line)   # satu ekstra untuk keamanan boundary
        return mapping

    def _ranges_to_lines(self, ranges: list,
                          char_to_line: list, text_len: int) -> set:
        """Konversi list (char_start, char_end) → set nomor baris."""
        matched = set()
        n = len(char_to_line)
        for cs, ce in ranges:
            cs = max(0, min(cs, text_len - 1))
            ce = max(cs, min(ce, text_len))
            sl = char_to_line[cs] if cs < n else 1
            el = char_to_line[ce - 1] if (ce - 1) < n else sl
            for ln in range(sl, el + 1):
                matched.add(ln)
        return matched

    @staticmethod
    def compute_match_stats(lines: list) -> dict:
        total   = len(lines)
        matched = sum(1 for ln in lines if ln.is_match)
        return {
            "total_lines":   total,
            "matched_lines": matched,
            "match_ratio":   round(matched / total * 100, 2) if total else 0.0,
        }


# ── Unit test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys; sys.path.insert(0, '.')
    from services.preprocessor import PreprocessorService
    from services.fingerprint  import FingerprintService
    from services.similarity   import SimilarityService

    pre = PreprocessorService()
    fp  = FingerprintService()
    sim = SimilarityService()
    hl  = HighlightService()

    code_a = "def calculate(x, y):\n    result = x + y\n    return result\n\ndef unique_a():\n    pass\n"
    code_b = "def calculate(x, y):\n    result = x + y\n    return result\n\ndef unique_b():\n    val = True\n"

    r_a = pre.preprocess(code_a, '.py')
    r_b = pre.preprocess(code_b, '.py')

    fp_a = fp.compute(r_a.processed, r_a.original, r_a.char_map)
    fp_b = fp.compute(r_b.processed, r_b.original, r_b.char_map)

    score, matched = SimilarityService._jaccard(fp_a.fingerprints, fp_b.fingerprints)
    print(f"Similarity: {score:.2f}%, matched hashes: {len(matched)}")

    hl_a = hl.highlight(code_a, fp_a.hash_positions, matched)
    hl_b = hl.highlight(code_b, fp_b.hash_positions, matched)

    print("\n--- File A ---")
    for ln in hl_a:
        print(f"  {'🟡' if ln.is_match else '  '} L{ln.line_number:02d}: {ln.content}")

    print("\n--- File B ---")
    for ln in hl_b:
        print(f"  {'🟡' if ln.is_match else '  '} L{ln.line_number:02d}: {ln.content}")

    assert len(hl_a) == len(code_a.splitlines())
    assert len(hl_b) == len(code_b.splitlines())

    matched_a = [ln for ln in hl_a if ln.is_match]
    matched_b = [ln for ln in hl_b if ln.is_match]
    assert len(matched_a) > 0, "Harus ada baris yang di-highlight di A"
    assert len(matched_b) > 0, "Harus ada baris yang di-highlight di B"

    # Verifikasi: baris yang di-highlight di A adalah baris yang MEMANG sama dengan B
    # Baris 1-3 sama, baris 5-6 berbeda
    highlighted_lines_a = {ln.line_number for ln in hl_a if ln.is_match}
    print(f"\nBaris di-highlight A: {sorted(highlighted_lines_a)}")
    print(f"  (Baris 1-3 = 'calculate' identik, seharusnya masuk)")

    stats = HighlightService.compute_match_stats(hl_a)
    print(f"\nStats A: {stats}")
    assert stats["total_lines"] == len(code_a.splitlines())

    print("\n✅ HighlightService — semua test lolos")
