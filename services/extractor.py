"""
ZipExtractorService
===================
Bertanggung jawab atas:
1. Membuka arsip .zip dari bytes (in-memory, tidak menulis ke disk)
2. Auto-detect dan strip "wrapper folder" di root ZIP jika ada
3. Mengidentifikasi setiap subfolder level-1 sebagai "project root" mahasiswa
4. Memfilter hanya file berekstensi .php, .dart, .py secara rekursif
5. Membaca konten file sebagai string UTF-8 (dengan fallback latin-1)

MASALAH YANG DISELESAIKAN — Wrapper Folder:
    Ketika pengguna membuat ZIP dengan cara:
        klik-kanan folder → "Compress to ZIP"
    hasilnya adalah:
        submissions.zip/
            submissions/          ← wrapper folder (sama nama dengan ZIP)
                ML-D_Marimar/
                    main.py
                ML-D_Pulgoso/
                    tugas.py
    
    Extractor mendeteksi ini secara otomatis:
    Jika SEMUA entri di ZIP berawal dengan satu folder yang sama,
    folder itu di-strip sebelum parsing project name.

Output kontrak:
    dict[str, dict[str, str]]
    {
        "ML-D_362258302025_Marimar": {
            "main.py":  "<raw source code>",
        },
        "ML-D_362258302026_Pulgoso": {
            "tugas.py": "<raw source code>",
        }
    }
"""

import io
import zipfile
from pathlib import PurePosixPath


ALLOWED_EXTENSIONS = {".php", ".dart", ".py"}


class ZipExtractorService:
    """
    Mengekstrak project mahasiswa dari arsip .zip ke memori.
    Tidak ada operasi baca/tulis ke filesystem — semua berjalan di RAM.
    """

    def __init__(self, zip_bytes: bytes) -> None:
        self._zip_bytes = zip_bytes

    def extract(self) -> dict[str, dict[str, str]]:
        """
        Membuka arsip dan mengembalikan peta project → file → source code.

        Returns:
            dict berisi semua project yang ditemukan beserta source code-nya.

        Raises:
            ValueError: Jika file bukan arsip .zip yang valid.
            ValueError: Jika tidak ada project folder yang ditemukan.
            ValueError: Jika tidak ada file .php/.dart/.py yang ditemukan.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(self._zip_bytes), "r")
        except zipfile.BadZipFile:
            raise ValueError(
                "File yang diunggah bukan arsip .zip yang valid. "
                "Pastikan file tidak rusak dan berformat .zip."
            )

        projects: dict[str, dict[str, str]] = {}

        with zf:
            all_names = zf.namelist()

            # --- LANGKAH 1: Deteksi dan strip wrapper folder ---
            # Contoh: ZIP berisi 'submissions/ML-D_A/main.py'
            # → strip_prefix = 'submissions/'
            strip_prefix = self._detect_wrapper_prefix(all_names)

            for member_path_str in all_names:
                # Lewati entry direktori
                if member_path_str.endswith("/"):
                    continue

                # Strip wrapper prefix jika ada
                effective_path = member_path_str
                if strip_prefix and effective_path.startswith(strip_prefix):
                    effective_path = effective_path[len(strip_prefix):]

                member_path = PurePosixPath(effective_path)
                parts = member_path.parts

                # Butuh minimal: ProjectFolder/file.py
                if len(parts) < 2:
                    continue

                project_name    = parts[0]
                file_extension  = PurePosixPath(parts[-1]).suffix.lower()

                # Filter ekstensi
                if file_extension not in ALLOWED_EXTENSIONS:
                    continue

                # Path relatif file dari dalam project root
                relative_file_path = str(PurePosixPath(*parts[1:]))

                # Baca konten file
                raw_bytes   = zf.read(member_path_str)
                source_code = self._decode_safely(raw_bytes, member_path_str)

                if not source_code.strip():
                    continue

                if project_name not in projects:
                    projects[project_name] = {}

                projects[project_name][relative_file_path] = source_code

        if not projects:
            raise ValueError(
                "Tidak ada project folder yang ditemukan di dalam .zip. "
                "Pastikan struktur arsip:\n"
                "  submissions.zip/\n"
                "    NamaProject_A/\n"
                "      file.py\n"
                "    NamaProject_B/\n"
                "      file.py"
            )

        # Hapus project tanpa file yang lolos filter
        projects = {name: files for name, files in projects.items() if files}

        if not projects:
            raise ValueError(
                "Tidak ada file .php, .dart, atau .py yang ditemukan "
                "di dalam arsip. Pastikan project berisi file dengan ekstensi tersebut."
            )

        if len(projects) < 2:
            names = list(projects.keys())
            raise ValueError(
                f"Hanya ditemukan 1 project ('{names[0]}'). "
                "Diperlukan minimal 2 project untuk perbandingan. "
                "Pastikan ZIP berisi folder dari beberapa mahasiswa."
            )

        return projects

    @staticmethod
    def _detect_wrapper_prefix(all_names: list[str]) -> str:
        """
        Mendeteksi apakah semua entri ZIP berada di dalam satu folder wrapper.

        Kasus yang ditangani:
            submissions.zip/
                submissions/      ← wrapper folder
                    ML-D_A/main.py
                    ML-D_B/tugas.py
        
        Algoritma:
        1. Ambil semua entri yang bukan direktori kosong
        2. Ekstrak nama folder level-1 dari setiap entri
        3. Jika semua entri berasal dari satu folder level-1 yang sama → itu wrapper
        4. Jika ada entri dari lebih dari satu folder level-1 → tidak ada wrapper

        Returns:
            String prefix yang harus di-strip (misal: 'submissions/')
            atau string kosong '' jika tidak ada wrapper folder.
        """
        # Hanya pertimbangkan entri file (bukan direktori kosong)
        file_entries = [n for n in all_names if not n.endswith("/")]

        if not file_entries:
            return ""

        # Ambil folder level-1 dari setiap entri
        level1_folders = set()
        for entry in file_entries:
            parts = PurePosixPath(entry).parts
            if len(parts) >= 2:
                # Entri di dalam subfolder → folder level-1 adalah parts[0]
                level1_folders.add(parts[0])
            else:
                # Entri langsung di root ZIP (misal: 'readme.txt')
                # Berarti tidak ada wrapper folder tunggal
                level1_folders.add("")

        # Wrapper folder terdeteksi hanya jika:
        # - Ada tepat SATU folder level-1
        # - Tidak ada file langsung di root ("")
        if len(level1_folders) == 1 and "" not in level1_folders:
            wrapper_name = level1_folders.pop()

            # Verifikasi: apakah di dalam wrapper ada LEBIH dari satu subfolder?
            # Jika hanya ada satu subfolder, itu mungkin memang struktur yang benar
            # (bukan wrapper tapi project tunggal)
            subfolders_in_wrapper = set()
            for entry in file_entries:
                parts = PurePosixPath(entry).parts
                if len(parts) >= 3:
                    # parts[0]=wrapper, parts[1]=project subfolder
                    subfolders_in_wrapper.add(parts[1])

            if len(subfolders_in_wrapper) >= 2:
                # Ada 2+ subfolder di dalam wrapper → ini adalah wrapper folder
                return wrapper_name + "/"

        return ""

    @staticmethod
    def _decode_safely(raw_bytes: bytes, filepath: str) -> str:
        """Dekode bytes ke string: UTF-8 → fallback Latin-1."""
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import io as _io
    import zipfile as _zf

    # --- Test 1: Struktur normal (tanpa wrapper) ---
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, "w") as z:
        z.writestr("Marimar/main.py",   "def hello(): pass")
        z.writestr("Marimar/utils.py",  "x = 1")
        z.writestr("Pulgoso/tugas.py",  "def hello(): pass")

    svc = ZipExtractorService(buf.getvalue())
    result = svc.extract()
    assert "Marimar" in result, "Marimar harus ada"
    assert "Pulgoso" in result, "Pulgoso harus ada"
    assert "main.py" in result["Marimar"]
    print("✅ Test 1 — Struktur normal: LOLOS")

    # --- Test 2: Struktur dengan wrapper folder (kasus user) ---
    buf2 = _io.BytesIO()
    with _zf.ZipFile(buf2, "w") as z:
        z.writestr("submissions/ML-D_Marimar/main.py",  "def hello(): pass")
        z.writestr("submissions/ML-D_Marimar/utils.py", "x = 1")
        z.writestr("submissions/ML-D_Pulgoso/tugas.py", "def hello(): pass")
        z.writestr("submissions/ML-D_Pulgoso/.vscode/settings.json", "{}")

    svc2 = ZipExtractorService(buf2.getvalue())
    result2 = svc2.extract()
    assert "ML-D_Marimar" in result2, f"ML-D_Marimar harus ada, dapat: {list(result2.keys())}"
    assert "ML-D_Pulgoso" in result2, f"ML-D_Pulgoso harus ada"
    assert "main.py"  in result2["ML-D_Marimar"]
    assert "tugas.py" in result2["ML-D_Pulgoso"]
    print(f"✅ Test 2 — Wrapper folder 'submissions/': LOLOS → {list(result2.keys())}")

    # --- Test 3: Hanya 1 project → harus raise ValueError ---
    buf3 = _io.BytesIO()
    with _zf.ZipFile(buf3, "w") as z:
        z.writestr("submissions/OnlyOne/main.py", "x = 1")

    try:
        ZipExtractorService(buf3.getvalue()).extract()
        assert False, "Harus raise ValueError"
    except ValueError as e:
        assert "1 project" in str(e) or "minimal 2" in str(e).lower() or "Hanya" in str(e)
        print(f"✅ Test 3 — Single project ValueError: LOLOS")

    # --- Test 4: Simulasi submissions.zip user persis ---
    buf4 = _io.BytesIO()
    with _zf.ZipFile(buf4, "w") as z:
        z.writestr("submissions/",                                        "")
        z.writestr("submissions/ML-D_362258302025_Marimar/",              "")
        z.writestr("submissions/ML-D_362258302025_Marimar/.vscode/",      "")
        z.writestr("submissions/ML-D_362258302025_Marimar/.vscode/settings.json", "{}")
        z.writestr("submissions/ML-D_362258302025_Marimar/main.py",       "import os\ndef main(): pass")
        z.writestr("submissions/ML-D_362258302026_Pulgoso/",              "")
        z.writestr("submissions/ML-D_362258302026_Pulgoso/.vscode/",      "")
        z.writestr("submissions/ML-D_362258302026_Pulgoso/.vscode/settings.json", "{}")
        z.writestr("submissions/ML-D_362258302026_Pulgoso/tugas.py",      "import os\ndef task(): pass")

    svc4 = ZipExtractorService(buf4.getvalue())
    result4 = svc4.extract()
    assert "ML-D_362258302025_Marimar" in result4
    assert "ML-D_362258302026_Pulgoso" in result4
    assert "main.py"  in result4["ML-D_362258302025_Marimar"]
    assert "tugas.py" in result4["ML-D_362258302026_Pulgoso"]
    print(f"✅ Test 4 — Simulasi submissions.zip user: LOLOS → {list(result4.keys())}")

    # --- Test 5: File langsung di root (tanpa project subfolder) ---
    buf5 = _io.BytesIO()
    with _zf.ZipFile(buf5, "w") as z:
        z.writestr("ProjectA/main.py", "x=1")
        z.writestr("ProjectB/main.py", "y=2")
        z.writestr("readme.txt",       "docs")  # file di root

    svc5 = ZipExtractorService(buf5.getvalue())
    prefix5 = svc5._detect_wrapper_prefix(buf5.getvalue() and _zf.ZipFile(_io.BytesIO(buf5.getvalue())).namelist())
    # readme.txt di root → level1_folders berisi "" → tidak ada wrapper
    assert prefix5 == "", f"Tidak boleh ada wrapper prefix, dapat: {repr(prefix5)}"
    print(f"✅ Test 5 — File di root ZIP → tidak ada wrapper: LOLOS")

    print("\n✅ ZipExtractorService — semua test LOLOS")