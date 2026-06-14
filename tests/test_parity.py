"""
test_parity.py
==============
Pengujian otomatis: verifikasi hasil pipeline Python identik dengan
nilai ground truth dari perhitungan manual Excel.

Cara menjalankan:
    python -m tests.test_parity                  # dari direktori jinggoplag/
    python -m pytest tests/test_parity.py -v     # jika pytest tersedia

Nilai ground truth diambil dari Winnowing_Plagiarism_Detection.xlsx
yang sudah diverifikasi manual, menggunakan submissions.zip.

Ground truth (submissions.zip — emoji sudah dihapus dari tugas.py):
    |FP1| = 194
    |FP2| = 200
    Intersection = 106
    Union = 288
    Jaccard = 36.8055555556%
    Threshold = Moderat
"""

import io
import sys
import zipfile

sys.path.insert(0, ".")

from services.extractor    import ZipExtractorService
from services.fingerprint  import FingerprintService
from services.preprocessor import PreprocessorService
from services.similarity   import SimilarityService
from services.highlighter  import HighlightService

# ── Ground truth dari Excel manual (dikonfirmasi) ─────────────────────────────
EXPECTED_FP1        = 194
EXPECTED_FP2        = 200
EXPECTED_INTER      = 106
EXPECTED_UNION      = 288
EXPECTED_JACCARD_RAW    = 36.8055555556   # nilai presisi dari Excel (belum dibulatkan)
EXPECTED_JACCARD_ROUNDED = 36.81           # nilai setelah round(..., 2) di SimilarityService
EXPECTED_THRESHOLD  = "Moderate"           # sistem menggunakan bahasa Inggris
TOLERANCE           = 0.001                # toleransi persentase (0.001%)

# Path ZIP — ubah sesuai lokasi pengujian
ZIP_PATH = "tests/fixtures/submissions.zip"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_zip(path: str) -> bytes:
    """Load ZIP dari file path atau fixture built-in."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return _build_inline_fixture()


def _build_inline_fixture() -> bytes:
    """
    Bangun ZIP minimal inline (tanpa file eksternal).
    Digunakan jika tests/fixtures/submissions.zip tidak tersedia.

    Source code ini mereplikasi struktur submissions.zip asli
    agar pengujian tetap bisa berjalan di CI tanpa asset eksternal.
    """
    main_py = (
        "import os\r\nimport CRUD as CRUD\r\n\r\n"
        "if __name__ == \"__main__\":\r\n"
        "    sistem_operasi = os.name\r\n\r\n"
        "    match sistem_operasi:\r\n"
        "        case \"posix\": os.system(\"clear\")\r\n"
        "        case \"nt\": os.system(\"cls\")\r\n\r\n"
        "    print(\"SELAMAT DATANG DI PROGRAM\")\r\n"
        "    print(\"DATABASE PERPUSTAKAAN\")\r\n"
        "    print(\"=========================\")\r\n"
        "    # check database itu ada atau tidak\r\n"
        "    CRUD.init_console()\r\n"
        "    while(True):\r\n"
        "        match sistem_operasi:\r\n"
        "            case \"posix\": os.system(\"clear\")\r\n"
        "            case \"nt\": os.system(\"cls\")\r\n"
        "        print(\"SELAMAT DATANG DI PROGRAM\")\r\n"
        "        print(\"DATABASE PERPUSTAKAAN\")\r\n"
        "        print(\"=========================\")\r\n"
        "        print(f\"1. Read Data\")\r\n"
        "        print(f\"2. Create Data\")\r\n"
        "        print(f\"3. Update Data\")\r\n"
        "        print(f\"4. Delete Data\\n\")\r\n"
        "        user_option = input(\"Masukan opsi: \")\r\n"
        "        match user_option:\r\n"
        "            case \"1\": CRUD.read_console()\r\n"
        "            case \"2\": CRUD.create_console()\r\n"
        "            case \"3\": CRUD.update_console()\r\n"
        "            case \"4\": CRUD.delete_console()\r\n"
        "        is_done = input(\"Apakah Selesai (y/n)? \")\r\n"
        "        if is_done == \"y\" or is_done == \"Y\":\r\n"
        "            break\r\n"
        "    print(\"Program Berakhir, Terima Kasiih KAKAAAAA\")\r\n"
    )

    tugas_py = (
        "import os\r\nimport CRUD as crud_module\r\n\r\n"
        "def clear_terminal(os_type: str):\r\n"
        "    match os_type:\r\n"
        "        case \"posix\":\r\n"
        "            os.system(\"clear\")\r\n"
        "        case \"nt\":\r\n"
        "            os.system(\"cls\")\r\n\r\n"
        "def show_header():\r\n"
        "    print(\"SELAMAT DATANG DI APLIKASI\")\r\n"
        "    print(\"MANAJEMEN DATABASE PERPUSTAKAAN\")\r\n"
        "    print(\"=\" * 25)\r\n\r\n"
        "if __name__ == \"__main__\":\r\n"
        "    os_type = os.name\r\n"
        "    clear_terminal(os_type)\r\n"
        "    show_header()\r\n"
        "    # inisialisasi database\r\n"
        "    crud_module.init_console()\r\n"
        "    while True:\r\n"
        "        clear_terminal(os_type)\r\n"
        "        show_header()\r\n"
        "        print(\"1. Read Data\")\r\n"
        "        print(\"2. Create Data\")\r\n"
        "        print(\"3. Update Data\")\r\n"
        "        print(\"4. Delete Data\\n\")\r\n"
        "        menu_choice = input(\"Masukkan opsi: \")\r\n"
        "        match menu_choice:\r\n"
        "            case \"1\": crud_module.read_console()\r\n"
        "            case \"2\": crud_module.create_console()\r\n"
        "            case \"3\": crud_module.update_console()\r\n"
        "            case \"4\": crud_module.delete_console()\r\n"
        "        finish = input(\"Selesai (y/n)? \")\r\n"
        "        if finish.lower() == \"y\":\r\n"
        "            break\r\n"
        "    print(\"Program selesai, terima kasih.\")\r\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("ML-D_362258302025_Marimar/main.py",  main_py)
        zf.writestr("ML-D_362258302026_Pulgoso/tugas.py", tugas_py)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Suite
# ─────────────────────────────────────────────────────────────────────────────

class ParityTestSuite:
    """Menjalankan semua pengujian paritas Excel vs sistem."""

    def __init__(self) -> None:
        self.passed  = 0
        self.failed  = 0
        self._errors: list = []

    # ── Assert helper ─────────────────────────────────────────────────────────

    def _assert(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            msg = f"  ❌ {name}" + (f" — {detail}" if detail else "")
            print(msg)
            self._errors.append(msg)

    def _assert_eq(self, name: str, got, expected, fmt: str = "") -> None:
        ok = (got == expected)
        detail = f"got={got:{fmt}}, expected={expected:{fmt}}" if not ok else ""
        self._assert(name, ok, detail)

    def _assert_close(self, name: str, got: float, expected: float,
                      tol: float = TOLERANCE) -> None:
        ok = abs(got - expected) <= tol
        detail = f"got={got:.10f}, expected={expected:.10f}, tol={tol}" if not ok else ""
        self._assert(name, ok, detail)

    # ── Tests ─────────────────────────────────────────────────────────────────

    def test_preprocessing(self, raw1: str, raw2: str,
                           r1, r2) -> None:
        """T1 — Preprocessing menghasilkan teks tanpa komentar dan whitespace."""
        print("\n[T1] Preprocessing")
        self._assert("P1: komentar # dihapus",
                     "check database" not in r1.processed)
        self._assert("P2: komentar # dihapus",
                     "inisialisasi" not in r2.processed)
        self._assert("P1: tidak ada whitespace",
                     " " not in r1.processed and "\n" not in r1.processed)
        self._assert("P2: tidak ada whitespace",
                     " " not in r2.processed and "\n" not in r2.processed)
        self._assert("P1: semua huruf kecil",
                     r1.processed == r1.processed.lower())
        self._assert("P2: semua huruf kecil",
                     r2.processed == r2.processed.lower())
        self._assert("P1: char_map panjang == processed",
                     len(r1.char_map) == len(r1.processed))
        self._assert("P2: char_map panjang == processed",
                     len(r2.char_map) == len(r2.processed))
        self._assert_eq("P1: panjang processed", len(r1.processed), 805)
        self._assert_eq("P2: panjang processed", len(r2.processed), 745)

    def test_char_map_accuracy(self, r1, r2) -> None:
        """T2 — char_map memetakan setiap karakter secara akurat."""
        print("\n[T2] Char Map Accuracy")
        for label, result in [("P1", r1), ("P2", r2)]:
            errors = [
                i for i, orig_idx in enumerate(result.char_map)
                if result.original.lower()[orig_idx] != result.processed[i]
            ]
            self._assert(
                f"{label}: char_map[i] → original[i] akurat (0 error)",
                len(errors) == 0,
                f"{len(errors)} mismatch ditemukan",
            )

    def test_rolling_hash(self, r1) -> None:
        """T3 — Rolling hash identik dengan hash naif untuk setiap k-gram."""
        print("\n[T3] Rolling Hash Rabin-Karp")

        def naive_hash(text: str, base: int = 256, mod: int = 1_000_000_007) -> int:
            result = 0
            for ch in text:
                result = (result * base + ord(ch)) % mod
            return result

        fp_svc = FingerprintService()
        kgrams = fp_svc._rolling_hash(r1.processed)  # noqa: SLF001

        mismatches = [
            i for i, (h, start) in enumerate(kgrams[:50])
            if h != naive_hash(r1.processed[start:start + 5])
        ]
        self._assert(
            "Rolling hash == naif hash (50 k-gram pertama)",
            len(mismatches) == 0,
            f"{len(mismatches)} mismatch",
        )
        self._assert_eq("Jumlah k-gram P1", len(kgrams), 801)

    def test_fingerprint_counts(self, fp1, fp2) -> None:
        """T4 — Jumlah fingerprint unik sesuai ground truth Excel."""
        print("\n[T4] Fingerprint Counts")
        self._assert_eq("|FP1| unik", len(fp1.fingerprints), EXPECTED_FP1)
        self._assert_eq("|FP2| unik", len(fp2.fingerprints), EXPECTED_FP2)

    def test_jaccard_components(self, fp1, fp2) -> None:
        """T5 — Intersection, Union, dan Jaccard sesuai ground truth Excel."""
        print("\n[T5] Jaccard Similarity")
        inter = fp1.fingerprints & fp2.fingerprints
        union = fp1.fingerprints | fp2.fingerprints
        jaccard_pct = len(inter) / len(union) * 100

        self._assert_eq("Intersection", len(inter),  EXPECTED_INTER)
        self._assert_eq("Union",         len(union),  EXPECTED_UNION)
        self._assert_close("Jaccard (%) raw vs Excel GT", jaccard_pct, EXPECTED_JACCARD_RAW)

    def test_threshold(self, results) -> None:
        """T6 — Kategori threshold sesuai aturan sistem."""
        print("\n[T6] Threshold Categorization")
        top = results[0]
        self._assert_eq("Threshold teratas",    top.threshold, EXPECTED_THRESHOLD)
        self._assert(   "Similarity > 30%",     top.similarity > 30.0)
        self._assert(   "Similarity <= 80%",    top.similarity <= 80.0)
        self._assert_close("Similarity (%) top (rounded)", top.similarity, EXPECTED_JACCARD_ROUNDED, tol=0.005)

    def test_highlight_coverage(self, raw1: str, raw2: str,
                                fp1, fp2, results) -> None:
        """T7 — HighlightService meng-highlight baris yang benar."""
        print("\n[T7] Highlight Coverage")
        hl_svc = HighlightService()
        matched = results[0].file_pairs[0].matched_hashes

        hl_a = hl_svc.highlight(raw1, fp1.hash_positions, matched)
        hl_b = hl_svc.highlight(raw2, fp2.hash_positions, matched)

        matched_a = sum(1 for ln in hl_a if ln.is_match)
        matched_b = sum(1 for ln in hl_b if ln.is_match)

        self._assert("A: ada baris yang di-highlight",    matched_a > 0)
        self._assert("B: ada baris yang di-highlight",    matched_b > 0)
        self._assert("A: tidak semua baris di-highlight", matched_a < len(hl_a))
        self._assert("B: tidak semua baris di-highlight", matched_b < len(hl_b))
        self._assert_eq("A: total baris",   len(hl_a), len(raw1.splitlines()))
        self._assert_eq("B: total baris",   len(hl_b), len(raw2.splitlines()))

        print(f"     A: {matched_a}/{len(hl_a)} baris di-highlight")
        print(f"     B: {matched_b}/{len(hl_b)} baris di-highlight")

    def test_zip_wrapper_detection(self) -> None:
        """T8 — Extractor menangani ZIP dengan wrapper folder."""
        print("\n[T8] ZIP Wrapper Folder Detection")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("submissions/ProjectA/main.py", "def hello(): pass")
            zf.writestr("submissions/ProjectB/tugas.py", "def hello(): pass")
        svc = ZipExtractorService(buf.getvalue())
        projects = svc.extract()
        self._assert("Wrapper 'submissions/' terdeteksi dan di-strip",
                     "ProjectA" in projects and "ProjectB" in projects)
        self._assert("Tidak ada key 'submissions' di projects",
                     "submissions" not in projects)

    def test_single_project_raises(self) -> None:
        """T9 — ZIP dengan 1 project menghasilkan ValueError."""
        print("\n[T9] Single Project Error Handling")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("OnlyProject/main.py", "x = 1")
        try:
            ZipExtractorService(buf.getvalue()).extract()
            self._assert("ValueError raised untuk 1 project", False, "Tidak ada exception")
        except ValueError:
            self._assert("ValueError raised untuk 1 project", True)

    def test_no_code_files_raises(self) -> None:
        """T10 — ZIP tanpa .py/.php/.dart menghasilkan ValueError."""
        print("\n[T10] No Supported Files Error Handling")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("ProjectA/readme.txt", "docs")
            zf.writestr("ProjectB/image.png",  "binary")
        try:
            ZipExtractorService(buf.getvalue()).extract()
            self._assert("ValueError raised untuk no .py files", False, "Tidak ada exception")
        except ValueError:
            self._assert("ValueError raised untuk no .py files", True)

    # ── Run all ───────────────────────────────────────────────────────────────

    def run(self) -> bool:
        """Jalankan seluruh suite dan kembalikan True jika semua lulus."""
        print("=" * 60)
        print("JINGGO PLAG — Test Parity Suite (Excel vs Sistem)")
        print("=" * 60)

        # ── Load data ─────────────────────────────────────────────────────────
        zip_bytes = load_zip(ZIP_PATH)
        extractor = ZipExtractorService(zip_bytes)
        projects  = extractor.extract()

        proj_keys = list(projects.keys())
        assert len(proj_keys) == 2, f"Butuh 2 project, dapat {len(proj_keys)}"

        key_a = next(k for k in proj_keys if "Marimar" in k or "main" in k)
        key_b = next(k for k in proj_keys if "Pulgoso" in k or "tugas" in k)

        raw1 = list(projects[key_a].values())[0]
        raw2 = list(projects[key_b].values())[0]

        pre = PreprocessorService()
        r1  = pre.preprocess(raw1, ".py")
        r2  = pre.preprocess(raw2, ".py")

        fp_svc = FingerprintService()
        fp1    = fp_svc.compute(r1.processed, r1.original, r1.char_map)
        fp2    = fp_svc.compute(r2.processed, r2.original, r2.char_map)

        sim_svc = SimilarityService()
        results = sim_svc.compute_all(
            {key_a: {"main.py": fp1}, key_b: {"tugas.py": fp2}}
        )

        # ── Run tests ─────────────────────────────────────────────────────────
        self.test_preprocessing(raw1, raw2, r1, r2)
        self.test_char_map_accuracy(r1, r2)
        self.test_rolling_hash(r1)
        self.test_fingerprint_counts(fp1, fp2)
        self.test_jaccard_components(fp1, fp2)
        self.test_threshold(results)
        self.test_highlight_coverage(raw1, raw2, fp1, fp2, results)
        self.test_zip_wrapper_detection()
        self.test_single_project_raises()
        self.test_no_code_files_raises()

        # ── Summary ───────────────────────────────────────────────────────────
        total = self.passed + self.failed
        print()
        print("=" * 60)
        print(f"HASIL: {self.passed}/{total} lulus")
        if self.failed:
            print(f"GAGAL ({self.failed}):")
            for err in self._errors:
                print(f"  {err}")
        else:
            print("✅ SEMUA TEST LOLOS — sistem paritas dengan Excel terkonfirmasi")
        print("=" * 60)

        return self.failed == 0


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Jalankan suite dari command line."""
    suite  = ParityTestSuite()
    passed = suite.run()
    sys.exit(0 if passed else 1)


# Compat: pytest dapat menemukan test_ functions di level module
def test_full_parity() -> None:
    """Satu test function untuk pytest compatibility."""
    suite  = ParityTestSuite()
    passed = suite.run()
    assert passed, "Ada test yang gagal — lihat output di atas"


if __name__ == "__main__":
    main()
