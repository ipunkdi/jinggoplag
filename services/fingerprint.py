"""
FingerprintService
==================
Pipeline fingerprinting tiga tahap:

  1. K-GRAM FORMATION  — sliding window panjang k
  2. ROLLING HASH      — Rabin-Karp STANDAR O(n)
  3. WINNOWING         — pilih minimum tiap window, simpan sebagai SET unik

Rolling Hash Rabin-Karp STANDAR:
    H[0] = poly_hash(text[0:k])
    H[i] = (H[i-1] - text[i-1]*BASE^(k-1)) * BASE + text[i+k-1]  mod MOD
    Properti: H[i] == poly_hash(text[i:i+k]) untuk semua i.

Menggunakan char_map dari PreprocessorService untuk memetakan posisi
k-gram di processed_text ke posisi di original_text secara akurat 100%.
"""

from dataclasses import dataclass


K_GRAM_SIZE = 5
WINDOW_SIZE = 4
RABIN_BASE  = 256
RABIN_MOD   = 1_000_000_007


@dataclass
class FingerprintResult:
    """Container hasil fingerprinting satu file."""

    fingerprints:   set   # set hash unik — input SimilarityService
    hash_positions: list  # [(hash_value, orig_char_start, orig_char_end), ...]


class FingerprintService:
    """Menghasilkan fingerprint digital dari processed text source code."""

    def __init__(
        self,
        k: int = K_GRAM_SIZE,
        w: int = WINDOW_SIZE,
        base: int = RABIN_BASE,
        mod: int = RABIN_MOD,
    ) -> None:
        """
        Args:
            k:    Ukuran k-gram.
            w:    Ukuran window winnowing.
            base: Base Rabin-Karp rolling hash.
            mod:  Modulus Rabin-Karp rolling hash.
        """
        self.k    = k
        self.w    = w
        self.base = base
        self.mod  = mod
        self._bk1 = pow(base, k - 1, mod)

    def compute(
        self,
        processed_text: str,
        char_map: list,
    ) -> FingerprintResult:
        """
        Jalankan pipeline: K-Gram → Rolling Hash → Winnowing → Position Mapping.

        Args:
            processed_text: Output PreprocessorService.processed.
            char_map:       Output PreprocessorService.char_map.

        Returns:
            FingerprintResult berisi fingerprints dan hash_positions.
        """
        if len(processed_text) < self.k:
            return FingerprintResult(fingerprints=set(), hash_positions=[])

        kgrams = self.rolling_hash(processed_text)
        if not kgrams:
            return FingerprintResult(fingerprints=set(), hash_positions=[])

        selected       = self._winnow(kgrams)
        hash_positions = self._map_positions(selected, char_map)
        fingerprints   = {hp[0] for hp in hash_positions}

        return FingerprintResult(
            fingerprints=fingerprints,
            hash_positions=hash_positions,
        )

    def rolling_hash(self, text: str) -> list:
        """
        Kembalikan [(hash_value, start_idx), ...] untuk setiap k-gram.

        Menggunakan Rolling Hash Rabin-Karp standar:
            H[i] = (H[i-1] - text[i-1]*BASE^(k-1)) * BASE + text[i+k-1]
        H[i] identik dengan poly_hash(text[i:i+k]) untuk semua i.
        """
        text_len  = len(text)
        kgram_len = self.k

        if text_len < kgram_len:
            return []

        result: list = []
        current_hash = 0

        for ch in text[:kgram_len]:
            current_hash = (current_hash * self.base + ord(ch)) % self.mod
        result.append((current_hash, 0))

        for i in range(1, text_len - kgram_len + 1):
            current_hash = (
                (current_hash - ord(text[i - 1]) * self._bk1) * self.base
                + ord(text[i + kgram_len - 1])
            ) % self.mod
            if current_hash < 0:
                current_hash += self.mod
            result.append((current_hash, i))

        return result

    def _winnow(self, kgrams: list) -> list:
        """
        Pilih minimum rightmost tiap window ukuran w.
        Kembalikan hanya perubahan minimum (deduplicated by position).
        """
        total = len(kgrams)
        if total < self.w:
            return [min(kgrams, key=lambda x: x[0])] if kgrams else []

        selected: list = []
        prev_min_idx = -1

        for window_start in range(total - self.w + 1):
            window = kgrams[window_start: window_start + self.w]

            min_val = None
            min_idx = -1
            for j in range(self.w - 1, -1, -1):
                if min_val is None or window[j][0] < min_val:
                    min_val = window[j][0]
                    min_idx = window_start + j

            if min_idx != prev_min_idx:
                selected.append(kgrams[min_idx])
                prev_min_idx = min_idx

        return selected

    def _map_positions(self, selected: list, char_map: list) -> list:
        """
        Peta akurat 100%: setiap k-gram di processed dipetakan ke posisi
        original menggunakan char_map dari PreprocessorService.

        Properti: char_map[i] = posisi processed[i] di original_text.
        K-gram processed[p:p+k] → original[char_map[p]:char_map[p+k-1]+1].
        """
        result: list  = []
        kgram_last    = self.k - 1

        for hash_val, proc_start in selected:
            proc_end_incl = proc_start + kgram_last
            if proc_end_incl >= len(char_map):
                continue
            orig_start = char_map[proc_start]
            orig_end   = char_map[proc_end_incl] + 1
            result.append((hash_val, orig_start, orig_end))

        return result
