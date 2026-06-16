"""
ZipExtractorService
===================
Membuka arsip .zip dari bytes (in-memory, tidak menulis ke disk),
mendeteksi dan men-strip wrapper folder otomatis, memfilter hanya
file .php/.dart/.py, lalu mengembalikan peta project → file → source.

Wrapper folder: ketika pengguna membuat ZIP dengan klik-kanan compress,
hasilnya submissions.zip/submissions/ProjectA/... — folder 'submissions'
di root ZIP di-strip secara otomatis.

Output:
    dict[str, dict[str, str]]
    {"ML-D_Marimar": {"main.py": "<code>"}, ...}
"""

import io
import zipfile
from pathlib import PurePosixPath


ALLOWED_EXTENSIONS: set = {".php", ".dart", ".py"}


class ZipExtractorService:
    """
    Mengekstrak project mahasiswa dari arsip .zip ke memori.
    Tidak ada operasi baca/tulis ke filesystem — semua berjalan di RAM.
    """

    def __init__(self, zip_bytes: bytes) -> None:
        """
        Args:
            zip_bytes: Konten mentah file .zip sebagai bytes.
        """
        self._zip_bytes = zip_bytes

    def extract(self) -> dict:
        """
        Buka arsip dan kembalikan peta project → file → source code.

        Returns:
            Dict berisi semua project yang ditemukan beserta source code-nya.

        Raises:
            ValueError: Jika bukan .zip valid, tidak ada project folder,
                        tidak ada file yang didukung, atau hanya 1 project.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(self._zip_bytes), "r")
        except zipfile.BadZipFile as exc:
            raise ValueError(
                "File yang diunggah bukan arsip .zip yang valid. "
                "Pastikan file tidak rusak dan berformat .zip."
            ) from exc

        projects: dict = {}

        with zf:
            all_names    = zf.namelist()
            strip_prefix = self.detect_wrapper_prefix(all_names)

            for member_path_str in all_names:
                if member_path_str.endswith("/"):
                    continue

                effective_path = member_path_str
                if strip_prefix and effective_path.startswith(strip_prefix):
                    effective_path = effective_path[len(strip_prefix):]

                member_path = PurePosixPath(effective_path)
                parts       = member_path.parts

                if len(parts) < 2:
                    continue

                project_name   = parts[0]
                file_extension = PurePosixPath(parts[-1]).suffix.lower()

                if file_extension not in ALLOWED_EXTENSIONS:
                    continue

                relative_file_path = str(PurePosixPath(*parts[1:]))
                raw_bytes          = zf.read(member_path_str)
                source_code        = self._decode_safely(raw_bytes)

                if not source_code.strip():
                    continue

                if project_name not in projects:
                    projects[project_name] = {}

                projects[project_name][relative_file_path] = source_code

        if not projects:
            raise ValueError(
                "Tidak ada project folder yang ditemukan di dalam .zip.\n"
                "Pastikan struktur arsip:\n"
                "  submissions.zip/\n"
                "    NamaProject_A/\n"
                "      file.py\n"
                "    NamaProject_B/\n"
                "      file.py"
            )

        projects = {name: files for name, files in projects.items() if files}

        if not projects:
            raise ValueError(
                "Tidak ada file .php, .dart, atau .py yang ditemukan "
                "di dalam arsip."
            )

        if len(projects) < 2:
            names = list(projects.keys())
            raise ValueError(
                f"Hanya ditemukan 1 project ('{names[0]}'). "
                "Diperlukan minimal 2 project untuk perbandingan."
            )

        return projects

    @staticmethod
    def detect_wrapper_prefix(all_names: list) -> str:
        """
        Deteksi apakah semua entri ZIP berada di dalam satu folder wrapper.

        Jika semua file ada di satu folder level-1 yang sama dan folder
        itu berisi 2+ subfolder, maka folder tersebut dianggap wrapper
        dan prefix-nya dikembalikan (mis. 'submissions/').

        Returns:
            Prefix yang harus di-strip, atau '' jika tidak ada wrapper.
        """
        file_entries = [n for n in all_names if not n.endswith("/")]

        if not file_entries:
            return ""

        level1_folders: set = set()
        for entry in file_entries:
            parts = PurePosixPath(entry).parts
            if len(parts) >= 2:
                level1_folders.add(parts[0])
            else:
                level1_folders.add("")

        if len(level1_folders) == 1 and "" not in level1_folders:
            wrapper_name = level1_folders.pop()

            subfolders: set = set()
            for entry in file_entries:
                parts = PurePosixPath(entry).parts
                if len(parts) >= 3:
                    subfolders.add(parts[1])

            if len(subfolders) >= 2:
                return wrapper_name + "/"

        return ""

    @staticmethod
    def _decode_safely(raw_bytes: bytes) -> str:
        """Dekode bytes ke string: UTF-8 → fallback Latin-1."""
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1")
