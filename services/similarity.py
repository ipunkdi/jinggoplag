"""
SimilarityService
=================
Menghitung dan mengagregasi skor Jaccard Similarity antar semua
pasangan proyek, dengan strategi Best Match Only untuk pencocokan file.

Threshold (dikonfirmasi):
    Rendah   : < 30%  → "Low"
    Moderat  : 30–80% → "Moderate"
    Tinggi   : > 80%  → "High"

Strategi Pencocokan File:
    Best Match Only — setiap file di Proyek A dipasangkan dengan satu
    file di Proyek B yang memiliki skor Jaccard tertinggi.

Output:
    list[ComparisonResult] — diurutkan dari similarity tertinggi.
"""

from dataclasses import dataclass, field
from itertools import combinations


THRESHOLD_LOW_MAX      = 30.0
THRESHOLD_MODERATE_MAX = 80.0


@dataclass
class FilePairResult:
    """Hasil perbandingan satu pasang file dari dua proyek berbeda."""

    file_a:         str
    file_b:         str
    similarity:     float
    threshold:      str
    matched_hashes: set = field(default_factory=set)


@dataclass
class ComparisonResult:
    """Hasil perbandingan satu pasang proyek."""

    project_a:  str
    project_b:  str
    similarity: float
    threshold:  str
    file_pairs: list = field(default_factory=list)


class SimilarityService:
    """
    Menghitung skor Jaccard Similarity antar semua pasangan proyek.

    Menggunakan strategi Best Match Only: setiap file di project A
    dipasangkan dengan file paling mirip di project B.
    """

    def compute_all(
        self,
        fingerprint_data: dict,
    ) -> list:
        """
        Hitung similarity untuk semua kombinasi pasangan proyek (n pilih 2).

        Args:
            fingerprint_data: Dict {project_name: {filename: FingerprintResult}}.

        Returns:
            List ComparisonResult diurutkan dari similarity tertinggi.
        """
        project_names = list(fingerprint_data.keys())
        comparisons: list = []

        for name_a, name_b in combinations(project_names, 2):
            comparison = self._compare_projects(
                name_a, fingerprint_data[name_a],
                name_b, fingerprint_data[name_b],
            )
            comparisons.append(comparison)

        comparisons.sort(key=lambda r: r.similarity, reverse=True)
        return comparisons

    def _compare_projects(
        self,
        name_a: str,
        files_a: dict,
        name_b: str,
        files_b: dict,
    ) -> ComparisonResult:
        """
        Bandingkan dua proyek dengan strategi Best Match Only.

        Untuk setiap file di Proyek A, cari file di Proyek B dengan
        skor Jaccard tertinggi. Agregasi = rata-rata similarity file pairs.
        """
        if not files_a or not files_b:
            return ComparisonResult(
                project_a=name_a,
                project_b=name_b,
                similarity=0.0,
                threshold=self.categorize(0.0),
                file_pairs=[],
            )

        file_pairs: list = []

        for file_a_name, fp_result_a in files_a.items():
            fingerprints_a: set = fp_result_a.fingerprints
            if not fingerprints_a:
                continue

            best_score   = 0.0
            best_file_b  = None
            best_matched: set = set()

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
                    threshold=self.categorize(best_score),
                    matched_hashes=best_matched,
                ))

        if not file_pairs:
            project_sim = 0.0
        else:
            project_sim = round(
                sum(fp.similarity for fp in file_pairs) / len(file_pairs), 2
            )

        file_pairs.sort(key=lambda fp: fp.similarity, reverse=True)

        return ComparisonResult(
            project_a=name_a,
            project_b=name_b,
            similarity=project_sim,
            threshold=self.categorize(project_sim),
            file_pairs=file_pairs,
        )

    @staticmethod
    def _jaccard(set_a: set, set_b: set) -> tuple:
        """
        Hitung Jaccard Similarity antara dua set fingerprint.

        Returns:
            Tuple (similarity_percent: float, intersection: set).
        """
        if not set_a and not set_b:
            return 0.0, set()

        intersection = set_a & set_b
        union        = set_a | set_b

        if not union:
            return 0.0, set()

        return len(intersection) / len(union) * 100.0, intersection

    @staticmethod
    def categorize(similarity: float) -> str:
        """
        Kategorikan persentase similarity ke dalam tiga tingkatan.

        Args:
            similarity: Persentase 0.0–100.0.

        Returns:
            "Low" jika < 30%, "Moderate" jika 30–80%, "High" jika > 80%.
        """
        if similarity < THRESHOLD_LOW_MAX:
            return "Low"
        if similarity <= THRESHOLD_MODERATE_MAX:
            return "Moderate"
        return "High"
