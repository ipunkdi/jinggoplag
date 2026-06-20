# Panduan Kontribusi

Terima kasih telah tertarik berkontribusi pada Jinggo Plag! Dokumen ini menjelaskan standar kode, alur kerja *pull request*, dan hal-hal yang perlu diperhatikan agar kontribusi Anda dapat diterima dengan lancar.

---

## Prasyarat

- Python 3.10 atau lebih baru
- Pemahaman dasar algoritma *string hashing* dan *set similarity* (lihat [`docs/ALGORITHM.md`](docs/ALGORITHM.md))
- Biasakan diri dengan arsitektur *service layer* sebelum mengubah kode (lihat [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md))

---

## Alur Kontribusi

```bash
# 1. Fork dan clone
git clone https://github.com/<username-anda>/jinggoplag.git
cd jinggoplag

# 2. Buat virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependensi runtime dan development
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Buat branch dari main
git checkout -b fix/nama-perbaikan-singkat
# atau
git checkout -b feat/nama-fitur-singkat

# 5. Kerjakan perubahan Anda
# ...

# 6. Pastikan test suite tetap 100% lulus
python -m tests.test_parity

# 7. Commit dengan format Conventional Commits (lihat di bawah)
git commit -m "fix(preprocessor): handle empty file gracefully"

# 8. Push dan buka Pull Request
git push origin fix/nama-perbaikan-singkat
```

---

## Standar Kode

### Gaya Penulisan

- Ikuti **PEP 8** — lebar baris maksimal **100 karakter**
- **Docstring wajib** pada setiap `class` dan `def` publik, menggunakan format Google-style:
  ```python
  def compute(self, processed_text: str, char_map: list) -> FingerprintResult:
      """
      Jalankan pipeline fingerprinting.

      Args:
          processed_text: Output PreprocessorService.processed.
          char_map:       Output PreprocessorService.char_map.

      Returns:
          FingerprintResult berisi fingerprints dan hash_positions.
      """
  ```
- Gunakan **type hints** pada semua parameter dan return value
- Gunakan `list[HighlightedLine]` (generik), **bukan** `List[HighlightedLine]` dari `typing` (untuk Python 3.10+)

### Aturan Khusus Proyek

| Aturan | Alasan |
|---|---|
| Jangan gunakan `st.*` di level modul pada file `pages/` atau `components/` | `set_page_config()` di `app.py::main()` wajib menjadi Streamlit command pertama — ini melanggar syarat tersebut |
| Jangan tulis file ke *filesystem* di `services/` | *Privacy by design* — seluruh pemrosesan harus berjalan di RAM |
| Jangan gunakan selector `.st-emotion-cache-*` di CSS | Class ini di-*generate* otomatis dan dapat berubah tanpa peringatan antar versi Streamlit; gunakan `data-testid` resmi |
| `char_map` wajib diteruskan ke `FingerprintService.compute()` | Memastikan *reverse mapping* posisi akurat 100% (bukan aproksimasi `str.find()`) |

### Aturan `except` yang Spesifik

Jangan gunakan `except Exception` secara umum:

```python
# ❌ Hindari
try:
    ...
except Exception as exc:
    ...

# ✅ Lebih baik
try:
    ...
except (ValueError, OSError) as exc:
    ...
```

---

## Format Conventional Commits

Semua pesan *commit* mengikuti format [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <deskripsi singkat dalam bahasa Inggris atau Indonesia>

[isi opsional — jelaskan mengapa, bukan apa]
```

### Tipe yang Digunakan

| Tipe | Kapan Digunakan |
|---|---|
| `feat` | Fitur baru |
| `fix` | Perbaikan *bug* |
| `refactor` | Restrukturisasi kode tanpa perubahan perilaku |
| `docs` | Perubahan dokumentasi saja |
| `test` | Menambah atau memperbaiki *test* |
| `chore` | Konfigurasi, CI, *dependency update* |
| `style` | Perubahan format/whitespace tanpa perubahan logika |

### Scope yang Relevan

`extractor`, `preprocessor`, `fingerprint`, `similarity`, `highlighter`, `navbar`, `upload`, `comparisons`, `result`, `detail`, `home`, `about`, `css`, `ci`, `tests`, `docs`, `app`

### Contoh

```
feat(preprocessor): add support for .ipynb file extension

Jupyter Notebook (.ipynb) adalah JSON yang berisi blok kode Python.
Tambahkan parser untuk mengekstrak isi 'source' setiap cell sebelum
preprocessing standar.

fix(css): replace emotion-cache selector with stable data-testid

.st-emotion-cache-* hash dapat berubah antar sesi/versi Streamlit.
Ganti dengan [data-testid="stAppViewContainer"] yang merupakan kontrak
stabil dari Streamlit.

docs(algorithm): clarify rightmost tie-breaking in Winnowing step
```

---

## Menambah Dukungan Bahasa Pemrograman Baru

Untuk menambahkan ekstensi baru (mis. `.js`, `.ipynb`):

1. **`services/preprocessor.py`**
   - Tambahkan entri di `_EXTENSION_MAP`
   - Implementasikan method `_strip_<bahasa>()` dengan regex yang membedakan komentar dari string literal

2. **`services/extractor.py`**
   - Tambahkan ekstensi ke `ALLOWED_EXTENSIONS`

3. **`tests/test_parity.py`**
   - Tambahkan *test case* yang memverifikasi preprocessing berjalan benar untuk bahasa baru

4. **Dokumentasi**
   - Perbarui daftar bahasa yang didukung di `README.md`

---

## Pull Request Checklist

Sebelum mengajukan *pull request*, pastikan seluruh item berikut terpenuhi:

- [ ] `python -m tests.test_parity` menghasilkan **39/39 lulus**
- [ ] Tidak ada *syntax error* baru (`python -c "import ast; ast.parse(open('file.py').read())"`)
- [ ] Semua fungsi dan kelas baru memiliki *docstring*
- [ ] Tidak ada `st.*` yang dipanggil di luar fungsi `render()` pada file `pages/` atau `components/`
- [ ] Tidak ada penulisan file ke *filesystem* di kode `services/`
- [ ] Pesan *commit* mengikuti format Conventional Commits
- [ ] Jika mengubah logika algoritma, tambahkan penjelasan di `docs/ALGORITHM.md`

---

## Melaporkan Bug

Buka *Issue* di GitHub dengan menyertakan:

1. Versi Python yang digunakan (`python --version`)
2. Versi Streamlit (`pip show streamlit`)
3. Deskripsi langkah yang menghasilkan bug
4. *Expected behavior* vs *actual behavior*
5. Jika memungkinkan, lampirkan `.zip` minimal yang mereproduksi masalah (pastikan tidak mengandung data mahasiswa nyata)
