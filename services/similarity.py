"""
SimilarityService
=================
Bertanggung jawab atas:
1. Menghitung skor kemiripan Jaccard antar pasangan fingerprint (file-level)
2. Memasangkan file antar proyek dengan strategi Best Match Only
3. Mengagregasi skor file-level menjadi skor project-level
4. Mengkategorikan skor ke dalam tiga tingkatan threshold
5. Mengurutkan hasil dari similarity tertinggi ke terendah

Parameter (dikonfirmasi developer):
    Threshold:
        Rendah   : < 30%  → "Low"    (orisinal / tidak signifikan)
        Moderat  : 30–80% → "Moderate" (terindikasi, perlu pemeriksaan manual)
        Tinggi   : > 80%  → "High"   (indikasi plagiarisme kuat)

Strategi Pencocokan File (dikonfirmasi):
    Opsi B — Best Match Only:
    Setiap file di Proyek A dipasangkan dengan satu file di Proyek B
    yang memiliki skor Jaccard tertinggi. File di Proyek B bisa
    digunakan oleh lebih dari satu file di Proyek A
    (many-to-one dari sisi A).

Output kontrak:
    list[ComparisonResult] — diurutkan dari similarity tertinggi

    ComparisonResult {
        project_a:   str
        project_b:   str
        similarity:  float   # persentase 0.0–100.0 (agregat project-level)
        threshold:   str     # "Low" | "Moderate" | "High"
        file_pairs:  list[FilePairResult]
    }

    FilePairResult {
        file_a:         str
        file_b:         str
        similarity:     float
        threshold:      str
        matched_hashes: set[int]   # irisan fingerprint — untuk HighlightService
    }
"""

from dataclasses import dataclass, field
from itertools import combinations
from pathlib import PurePosixPath


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------
THRESHOLD_LOW_MAX      = 30.0   # < 30%  → Low
THRESHOLD_MODERATE_MAX = 80.0   # 30–80% → Moderate
# > 80% → High


# ---------------------------------------------------------------------------
# Data classes (output contracts)
# ---------------------------------------------------------------------------

@dataclass
class FilePairResult:
    """Hasil perbandingan satu pasang file dari dua proyek berbeda."""
    file_a:         str
    file_b:         str
    similarity:     float        # 0.0 – 100.0
    threshold:      str          # "Low" | "Moderate" | "High"
    matched_hashes: set = field(default_factory=set)  # irisan fingerprint


@dataclass
class ComparisonResult:
    """Hasil perbandingan satu pasang proyek."""
    project_a:  str
    project_b:  str
    similarity: float            # 0.0 – 100.0 (rata-rata file pairs)
    threshold:  str              # "Low" | "Moderate" | "High"
    file_pairs: list = field(default_factory=list)   # list[FilePairResult]


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class SimilarityService:
    """
    Menghitung dan mengagregasi skor Jaccard Similarity antar semua
    pasangan proyek, dengan strategi Best Match Only untuk pencocokan file.
    """

    def compute_all(
        self,
        fingerprint_data: dict[str, dict[str, object]],
    ) -> list[ComparisonResult]:
        """
        Entry point utama. Menghitung similarity untuk semua kombinasi
        pasangan proyek (n pilih 2).

        Args:
            fingerprint_data: Struktur data dari FingerprintService
                {
                    "ProjectA": {
                        "main.py": FingerprintResult,
                        "utils.py": FingerprintResult,
                    },
                    "ProjectB": {
                        "tugas.py": FingerprintResult,
                    }
                }

        Returns:
            List ComparisonResult diurutkan dari similarity tertinggi ke terendah.
        """
        project_names = list(fingerprint_data.keys())
        results: list[ComparisonResult] = []

        # Iterasi semua pasangan proyek (kombinasi tanpa pengulangan)
        for name_a, name_b in combinations(project_names, 2):
            files_a = fingerprint_data[name_a]
            files_b = fingerprint_data[name_b]

            comparison = self._compare_projects(name_a, files_a, name_b, files_b)
            results.append(comparison)

        # Urutkan dari similarity tertinggi
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Project-level comparison
    # ------------------------------------------------------------------

    def _compare_projects(
        self,
        name_a: str,
        files_a: dict[str, object],
        name_b: str,
        files_b: dict[str, object],
    ) -> ComparisonResult:
        """
        Membandingkan dua proyek dengan strategi Best Match Only.

        Strategi Best Match Only:
        - Untuk setiap file di Proyek A, cari file di Proyek B yang
          menghasilkan skor Jaccard TERTINGGI
        - File di Proyek B bisa digunakan oleh lebih dari satu file A

        Agregasi project-level:
        - Similarity proyek = rata-rata dari semua file pair similarity

        Args:
            name_a:  Nama proyek A
            files_a: Dict {filename: FingerprintResult} proyek A
            name_b:  Nama proyek B
            files_b: Dict {filename: FingerprintResult} proyek B
        """
        file_pairs: list[FilePairResult] = []

        if not files_a or not files_b:
            return ComparisonResult(
                project_a=name_a,
                project_b=name_b,
                similarity=0.0,
                threshold=self._categorize(0.0),
                file_pairs=[],
            )

        for file_a_name, fp_result_a in files_a.items():
            fingerprints_a: set = fp_result_a.fingerprints

            if not fingerprints_a:
                continue

            best_score     = 0.0
            best_file_b    = None
            best_matched   = set()

            for file_b_name, fp_result_b in files_b.items():
                fingerprints_b: set = fp_result_b.fingerprints

                if not fingerprints_b:
                    continue

                score, matched = self._jaccard(fingerprints_a, fingerprints_b)

                if score > best_score:
                    best_score   = score
                    best_file_b  = file_b_name
                    best_matched = matched

            if best_file_b is not None:
                file_pairs.append(FilePairResult(
                    file_a=file_a_name,
                    file_b=best_file_b,
                    similarity=round(best_score, 2),
                    threshold=self._categorize(best_score),
                    matched_hashes=best_matched,
                ))

        if not file_pairs:
            project_sim = 0.0
        else:
            project_sim = sum(fp.similarity for fp in file_pairs) / len(file_pairs)
            project_sim = round(project_sim, 2)

        # Urutkan file pairs dari similarity tertinggi
        file_pairs.sort(key=lambda fp: fp.similarity, reverse=True)

        return ComparisonResult(
            project_a=name_a,
            project_b=name_b,
            similarity=project_sim,
            threshold=self._categorize(project_sim),
            file_pairs=file_pairs,
        )

    # ------------------------------------------------------------------
    # Jaccard Similarity
    # ------------------------------------------------------------------

    @staticmethod
    def _jaccard(
        set_a: set[int], set_b: set[int]
    ) -> tuple[float, set[int]]:
        """
        Menghitung Jaccard Similarity antara dua set fingerprint.

        Formula:
            J(A, B) = |A ∩ B| / |A ∪ B|

        Returns:
            Tuple (persentase_similarity, set_irisan)
            persentase_similarity: 0.0 – 100.0
        """
        if not set_a and not set_b:
            return 0.0, set()

        intersection = set_a & set_b
        union = set_a | set_b

        if not union:
            return 0.0, set()

        jaccard_score = len(intersection) / len(union) * 100.0
        return jaccard_score, intersection

    # ------------------------------------------------------------------
    # Threshold Categorization
    # ------------------------------------------------------------------

    @staticmethod
    def _categorize(similarity: float) -> str:
        """
        Mengkategorikan persentase similarity ke dalam tiga tingkatan.

        Args:
            similarity: Persentase 0.0 – 100.0

        Returns:
            "Low"      jika similarity < 30%
            "Moderate" jika 30% ≤ similarity ≤ 80%
            "High"     jika similarity > 80%
        """
        if similarity < THRESHOLD_LOW_MAX:
            return "Low"
        elif similarity <= THRESHOLD_MODERATE_MAX:
            return "Moderate"
        else:
            return "High"


# ---------------------------------------------------------------------------
# Unit test (jalankan: python services/similarity.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from services.fingerprint import FingerprintService, FingerprintResult

    fp_svc = FingerprintService(k=5, w=4, base=256, mod=1_000_000_007)
    sim_svc = SimilarityService()

    # Buat kode simulasi untuk 3 mahasiswa
    code_marimar = "def hello world python code fingerprint winnowing rabin karp jaccard"
    code_pulgoso = "def hello world python code fingerprint winnowing rabin karp jaccard"  # identik
    code_rodolfo = "totally different code with no similarity whatsoever here and there"

    def make_fp(code):
        return fp_svc.compute(code, code)

    fingerprint_data = {
        "Marimar_Root": {
            "main.py":  make_fp(code_marimar),
            "utils.py": make_fp("shared utility function for all projects here"),
        },
        "Pulgoso_Root": {
            "tugas.py": make_fp(code_pulgoso),
            "helper.py": make_fp("shared utility function for all projects here"),
        },
        "Rodolfo_Root": {
            "app.py":   make_fp(code_rodolfo),
        },
    }

    results = sim_svc.compute_all(fingerprint_data)

    assert len(results) == 3, f"3 proyek → 3 pasang (C(3,2)=3), dapat: {len(results)}"
    print(f"✅ Jumlah pasangan: {len(results)} (benar, C(3,2)=3)")

    # Pasangan pertama harus Marimar vs Pulgoso (identik)
    top = results[0]
    assert top.project_a in ("Marimar_Root", "Pulgoso_Root")
    assert top.project_b in ("Marimar_Root", "Pulgoso_Root")
    assert top.similarity == 100.0, f"Kode identik harus 100%, dapat: {top.similarity}"
    assert top.threshold == "High", f"100% harus High, dapat: {top.threshold}"
    print(f"✅ Top pair: {top.project_a} vs {top.project_b} = {top.similarity}% ({top.threshold})")

    # Verifikasi threshold
    assert sim_svc._categorize(0.0)   == "Low"
    assert sim_svc._categorize(29.9)  == "Low"
    assert sim_svc._categorize(30.0)  == "Moderate"
    assert sim_svc._categorize(80.0)  == "Moderate"
    assert sim_svc._categorize(80.1)  == "High"
    assert sim_svc._categorize(100.0) == "High"
    print("✅ Threshold categorization — semua batas benar")

    # Verifikasi urutan (sudah sorted descending)
    for i in range(len(results) - 1):
        assert results[i].similarity >= results[i+1].similarity, \
            "Hasil harus terurut dari similarity tertinggi"
    print("✅ Pengurutan descending — benar")

    # Verifikasi file_pairs ada dan matched_hashes terisi
    assert len(top.file_pairs) > 0, "file_pairs tidak boleh kosong"
    for fp_pair in top.file_pairs:
        assert isinstance(fp_pair.matched_hashes, set)
        print(f"   [{fp_pair.file_a} vs {fp_pair.file_b}] = {fp_pair.similarity}% ({fp_pair.threshold})")

    print("\n✅ SimilarityService — semua assertion lolos")

    # Print ringkasan
    print("\n--- Ringkasan Hasil ---")
    for r in results:
        print(f"  {r.project_a} vs {r.project_b}: {r.similarity}% [{r.threshold}]")
        for fp in r.file_pairs:
            print(f"    {fp.file_a} ↔ {fp.file_b}: {fp.similarity}%")