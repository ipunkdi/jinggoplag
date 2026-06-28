# Strategi & Metodologi Pengujian

Proyek ini menggunakan dua lapis pengujian yang saling melengkapi: **pengujian otomatis** (`pytest`/`unittest`-style) untuk lapisan logika/algoritma, dan **pengujian *black-box*** untuk lapisan antarmuka pengguna.

## 1. Pengujian Otomatis (`tests/test_parity.py`)

### Mengapa Disebut "Parity"?

Nama *parity* (kesetaraan) dipilih karena tujuan utama *test suite* ini bukan sekadar memeriksa "kode tidak *crash*", melainkan memverifikasi **kesetaraan numerik** antara hasil komputasi sistem dan *ground truth* yang dihitung manual menggunakan Microsoft Excel — sebuah sumber kebenaran independen dari kode Python.

### Cara Menjalankan

```bash
# Tanpa pytest (built-in __main__, exit code mencerminkan hasil)
python -m tests.test_parity

# Dengan pytest
pip install -r requirements-dev.txt
pytest tests/test_parity.py -v
```

### Data Uji

`tests/fixtures/submissions.zip` berisi dua *project root* nyata (`ML-D_362258302025_Marimar/main.py` dan `ML-D_362258302026_Pulgoso/tugas.py`) — program CRUD sederhana dengan kemiripan struktural sebagian, hasil dari pengujian skenario nyata yang juga dihitung manual di Excel.

### Cakupan 55 Assertion (14 Kelompok)

| ID | Nama | Apa yang Dibuktikan |
|---|---|---|
| T1 | Preprocessing | Komentar dan *whitespace* benar-benar terhapus; *case folding* konsisten; panjang teks akhir sesuai nilai yang sudah diverifikasi manual |
| T2 | Char Map Accuracy | Setiap elemen `char_map` memetakan balik ke karakter asli yang **benar**, diuji untuk **seluruh** indeks (bukan sampel) |
| T3 | Rolling Hash | Nilai *rolling hash* untuk 50 *k-gram* pertama identik dengan hash naif — membuktikan korektnasi rumus *rolling update* |
| T4 | Fingerprint Counts | `\|FP1\|` dan `\|FP2\|` sesuai nilai Excel (194 dan 200) |
| T5 | Jaccard Components | Intersection (106), Union (288), dan Jaccard (36.8056%) sesuai Excel hingga toleransi 0.001% |
| T6 | Threshold Categorization | Hasil akhir masuk kategori Moderat sesuai aturan ambang batas |
| T7 | Threshold Boundaries | Keenam titik batas (`29.9%→Low`, `30.0%→Moderate`, `80.0%→Moderate`, `80.1%→High`, dst.) diuji satu per satu |
| T8 | Highlight Coverage | Baris yang disorot bukan nol, bukan semua baris (pembuktian highlight bekerja proporsional, bukan *all-or-nothing*) |
| T9 | ZIP Wrapper Detection | *Wrapper folder* (mis. `submissions/`) terdeteksi dan di-*strip* otomatis |
| T10 | Single Project Error | `ValueError` informatif saat hanya 1 *project* ditemukan |
| T11 | No Supported Files Error | `ValueError` informatif saat tidak ada `.py`/`.php`/`.dart` ditemukan |
| T12 | PDF Report Generation | Header `%PDF` valid dan ukuran berkas > 0 byte untuk `summary_report` dan `detail_report`, menggunakan data nyata dari fixture |
| T13 | Code Comparison PDF Report | Header `%PDF` valid dan ukuran berkas > 0 byte untuk laporan kode berdampingan (*landscape*) dengan data *highlight* nyata |
| T14 | Graph Visualization | `GraphService` menghasilkan NetworkX Graph, statistik, dan SVG valid (ada `<circle>` dan `</svg>`) dari hasil nyata; penanganan graf kosong tidak *crash* |

### Integrasi Continuous Integration

Setiap `push` dan `pull request` ke *branch* `main` memicu `python -m tests.test_parity` secara otomatis lewat GitHub Actions (`.github/workflows/test.yml`). *Badge* status di README mencerminkan hasil terakhir.

## 2. Pengujian Black-Box (Alur UI)

Pengujian *black-box* memverifikasi perilaku sistem dari sudut pandang pengguna akhir, tanpa memeriksa implementasi internal. Skenario berikut dipakai dalam pengujian Tugas Akhir:

| Test Case ID | Deskripsi Test Case | Teknik | Precondition | Input | Expected Output | Kriteria Lulus |
|---|---|---|---|---|---|---|
| TC-BB-01 | Upload File ZIP Valid (Normal Case) | Equivalence Partitioning | Pengguna berada di halaman Upload; belum ada file yang diunggah. | ZIP berisi dua atau lebih subfolder project, masing-masing mengandung file `.py`, `.php`, atau `.dart`. | File diterima oleh komponen `file_uploader`, nama dan ukuran file ditampilkan di bawah tombol. | File terunggah tanpa pesan error, tombol START ANALYSIS aktif (tidak `disabled`). |
| TC-BB-02 | Proses Deteksi Berhasil (Normal Case) | Use Case Testing | File ZIP valid sudah berhasil diunggah (lanjutan TC-BB-01). | Menekan tombol START ANALYSIS pada file ZIP yang valid. | *Progress bar* muncul dan bergerak melewati 4 tahap (Ekstraksi → Preprocessing → Fingerprinting → Jaccard), kemudian halaman berpindah otomatis ke Comparisons (Step 2). | Halaman Comparisons tampil dengan tabel yang berisi minimal satu pasangan project dan nilai *similarity*-nya. |
| TC-BB-03 | Tampil Hasil Similarity (Normal Case) | Use Case Testing | Proses analisis sudah selesai dan data Jaccard tersimpan di `session_state` (lanjutan TC-BB-02). | Data hasil komputasi Jaccard yang sudah tersimpan di `session_state`. | Halaman Comparisons menampilkan tabel dengan kolom Index, Submissions in Comparison, Similarity (dengan *badge* warna *threshold*), dan ikon mata. Halaman Result menampilkan OVERVIEW, Total Similarity, dan tabel *file-level*. | Nilai persentase muncul benar, *badge* berwarna sesuai *threshold* (Hijau=Rendah, Oranye=Moderat, Merah=Tinggi), navigasi antar halaman berfungsi. |
| TC-BB-04 | ZIP dengan Satu Project Saja (Boundary Case) | Boundary Value Analysis | Pengguna berada di halaman Upload; belum ada file yang diunggah. | ZIP berisi hanya satu subfolder mahasiswa (satu *project root*), meskipun folder itu berisi banyak file. | Sistem menampilkan pesan error informatif: "Hanya ditemukan 1 project... Diperlukan minimal 2 project untuk perbandingan". | Pesan error tampil jelas di UI, sistem tidak *crash*, pengguna bisa mencoba upload ulang. |
| TC-BB-05 | ZIP Tanpa File Kode yang Didukung (Error Case) | Equivalence Partitioning | Pengguna berada di halaman Upload; belum ada file yang diunggah. | ZIP berisi file dengan ekstensi selain `.php`, `.dart`, `.py` (misalnya hanya `.txt`, `.png`, `.json`, atau `.pyc`). | Sistem menampilkan pesan error: "Tidak ada file .php, .dart, atau .py yang ditemukan di dalam arsip". | Pesan error tampil, tidak ada proses analisis yang berjalan, sistem tidak *crash*. |
| TC-BB-06 | Upload File Bukan ZIP (Error Case) | Equivalence Partitioning | Pengguna berada di halaman Upload; belum ada file yang diunggah. | File dengan ekstensi `.pdf`, `.txt`, atau `.docx`. | Komponen `file_uploader` Streamlit menolak file sebelum dikirim ke *backend* karena batasan `type=["zip"]`. | File tidak bisa dipilih atau ditolak langsung oleh UI, tidak ada pesan error dari *backend*. |
| TC-BB-07 | File ZIP Rusak/Corrupt (Error Case) | Error Guessing | Pengguna berada di halaman Upload; belum ada file yang diunggah. | File berekstensi `.zip` tetapi isinya rusak atau bukan arsip ZIP yang valid. | Sistem menampilkan pesan error: "File yang diunggah bukan arsip .zip yang valid". | Pesan error tampil dengan jelas, sistem tidak *crash*. |
| TC-BB-08 | Tombol START ANALYSIS Sebelum Upload (Edge Case) | State Transition Testing | Halaman Upload baru dibuka; `session_state` kosong (state awal). | Halaman Upload dibuka tanpa mengunggah file apapun. | Tombol START ANALYSIS dalam kondisi `disabled` (tidak bisa diklik), tidak ada aksi yang terpicu. | Tombol tampak abu-abu dan tidak responsif terhadap klik. |
| TC-BB-09 | Navigasi langsung ke Halaman Tengah (Edge Case) | State Transition Testing | Pengguna belum melalui tahap Upload; `session_state` belum memiliki data analisis. | Pengguna mencoba mengakses halaman Comparisons, Result, atau Detail tanpa melewati tahap Upload terlebih dahulu (misalnya dengan mengklik menu "Plagiarism Checker" dari halaman Home). | Sistem mendeteksi tidak ada data di `session_state` dan menampilkan pesan peringatan, kemudian mengarahkan pengguna ke halaman Upload. | Pengguna tidak bisa melihat halaman kosong atau mengalami *crash* akibat data yang belum ada. |
| TC-BB-10 | ZIP dengan Wrapper Folder (Normal Case) | Error Guessing | Pengguna berada di halaman Upload; belum ada file yang diunggah. | ZIP yang dibuat dengan cara klik-kanan *compress*, menghasilkan struktur `submissions.zip/submissions/ProjectA/main.py`. | Sistem mendeteksi otomatis *wrapper folder* `submissions/` dan tetap berhasil mengekstrak project dengan benar. | Analisis berjalan normal seolah tidak ada *wrapper folder*. |
| TC-BB-11 | Export PDF Ringkasan Kelas (Normal Case) | Use Case Testing | Data analisis tersedia di `session_state`; pengguna berada di halaman Comparisons (lanjutan TC-BB-02). | Klik tombol "Export PDF" pada halaman Comparisons. | Browser langsung memicu unduhan file PDF bernama `jinggoplag_ringkasan_[timestamp].pdf` tanpa langkah tambahan. | File PDF berhasil terunduh, dapat dibuka, berisi header "Laporan Ringkasan Deteksi Plagiarisme", tabel seluruh pasangan, dan statistik High/Moderate/Low. |
| TC-BB-12 | Export PDF Detail Pasangan (Normal Case) | Use Case Testing | Pengguna sudah memilih satu pasangan project dan berada di halaman Result. | Klik tombol "Export PDF" pada halaman Result. | Browser langsung memicu unduhan `jinggoplag_detail_[timestamp].pdf`. | File PDF terunduh, berisi nama Project A & B, skor Total Similarity, dan tabel pasangan file beserta *similarity*-nya. |
| TC-BB-13 | Export PDF Kode Berdampingan (Normal Case) | Use Case Testing | Pengguna berada di halaman Detail (Step 4) dengan dua file kode yang dibandingkan. | Klik tombol "Export PDF" pada halaman Detail. | Browser langsung memicu unduhan `jinggoplag_kode_[timestamp].pdf`. | File PDF terunduh, orientasi *landscape* (kertas horizontal), berisi dua kolom kode berdampingan dengan *highlight* kuning pada baris yang *fingerprint*-nya identik. |
| TC-BB-14 | Visualisasi Graf Kemiripan dan Filter (Normal Case) | Boundary Value Analysis & Use Case Testing | Data analisis tersedia di `session_state`; pengguna berada di halaman Comparisons. | Klik "Graf Kemiripan" di Comparisons, lalu geser *slider* minimum *similarity* dari 30% ke 80%. | Halaman Graf tampil dengan SVG jaringan *node-edge*, 4 metrik statistik, dan tabel top-10. Saat *slider* digeser, jumlah "Koneksi Terdeteksi" berkurang dan graf diperbarui *real-time*. | SVG tampil, setiap *node* mewakili satu project, garis menghubungkan pasangan sesuai *threshold slider*, nilai metrik berubah proporsional, sistem tidak *crash*. |
| TC-BB-15 | Pan dan Zoom Visualisasi Graf (Normal Case) | Use Case Testing / Exploratory Testing | Pengguna berada di halaman Graf dengan minimal satu *node* yang tampil. | Melakukan: (1) *scroll* mouse untuk *zoom*, (2) klik tahan + geser untuk *pan*, (3) klik tombol "↺ Reset". | (1) Area tampilan diperbesar/diperkecil dengan titik pusat di posisi kursor. (2) Area tampilan bergeser mengikuti arah *drag*. (3) Tampilan kembali ke posisi dan skala semula. | Simpul yang semula terpotong dapat dilihat setelah *pan/zoom*; *zoom* terpusat pada posisi kursor (bukan pojok kiri atas); tombol Reset mengembalikan transformasi ke *scale*=1 dan posisi awal. |

## 3. Evaluasi Akurasi (Uji Validitas Algoritma)

Karena sistem ini adalah instrumen deteksi langsung — bukan model *machine learning* dengan dataset berlabel — performa dinilai melalui **Uji Validitas Algoritma**: perbandingan langsung hasil komputasi sistem terhadap simulasi manual yang dijadikan acuan (*gold standard*).

**Prosedur:**

1. Simulasikan seluruh pipeline (Preprocessing → K-Gram → Hashing → Winnowing → Jaccard) secara manual menggunakan formula Microsoft Excel native, independen dari kode Python.
2. Bandingkan setiap komponen perantara (jumlah *fingerprint*, *intersection*, *union*) — bukan hanya hasil akhir — untuk memastikan kesetaraan di setiap tahap, bukan hanya kebetulan pada hasil akhir.
3. Verifikasi otomatis lewat `tests/test_parity.py` agar kesetaraan ini dapat direproduksi kapan saja tanpa pengecekan manual berulang.

Sistem dinyatakan valid karena seluruh komponen perantara dan hasil akhir identik dengan simulasi manual hingga presisi yang diuji (toleransi `0.001%` untuk akumulasi *floating point*).
