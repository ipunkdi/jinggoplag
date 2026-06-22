# 🔍 Jinggo Plag

**Sistem Deteksi Plagiarisme Source Code Berbasis Web**
menggunakan algoritma **Winnowing Fingerprinting** dengan **Rolling Hash Rabin-Karp** dan **Jaccard Similarity**.

[![Tests](https://github.com/ipunkdi/jinggoplag/actions/workflows/test.yml/badge.svg)](https://github.com/ipunkdi/jinggoplag/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Daftar Isi

- [Ringkasan](#ringkasan)
- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Cara Kerja Algoritma](#cara-kerja-algoritma)
  - [Justifikasi Akademik Nilai Threshold](#justifikasi-akademik-nilai-threshold)
- [Struktur Proyek](#struktur-proyek)
- [Instalasi & Menjalankan](#instalasi--menjalankan)
- [Format Input (.zip)](#format-input-zip)
- [Pengujian](#pengujian)
- [Verifikasi Akurasi (Excel Gold Standard)](#verifikasi-akurasi-excel-gold-standard)
- [Keterbatasan yang Diketahui](#keterbatasan-yang-diketahui)
- [Kontribusi](#kontribusi)
- [Lisensi](#lisensi)
- [Kredit](#kredit)

---

## Ringkasan

Jinggo Plag adalah aplikasi web *stand-alone* untuk menganalisis tingkat kemiripan (*similarity*) antar *source code* secara massal dari satu arsip `.zip` berisi banyak *submission* mahasiswa. Sistem ini dirancang untuk membantu tenaga pendidik memverifikasi orisinalitas tugas/proyek mahasiswa secara objektif dan transparan, termasuk menampilkan baris kode spesifik yang terindikasi identik antar dua *submission*.

Mendukung tiga bahasa pemrograman: **PHP**, **Dart**, dan **Python** — mencakup mata kuliah Pemrograman Web Dasar, Pemrograman Berorientasi Objek, dan Sistem Pendukung Keputusan.

Seluruh pemrosesan berjalan **di memori (volatile)** selama satu sesi — tidak ada *source code* yang ditulis atau disimpan permanen ke disk server, menjamin privasi karya mahasiswa.

## Fitur Utama

- **Pemrosesan skala repositori** — satu arsip `.zip` dapat berisi puluhan *project root* mahasiswa sekaligus; sistem membandingkan seluruh kombinasi pasangan secara otomatis.
- **Deteksi otomatis struktur arsip** — mendeteksi dan menghapus *wrapper folder* (mis. hasil "Compress to ZIP" yang membungkus semua folder ke satu folder induk tambahan).
- **Tahan terhadap modifikasi kosmetik dan penyalinan sebagian** — *preprocessing* menghapus komentar, *whitespace*, dan perbedaan kapitalisasi sebelum analisis, sehingga sistem tidak mudah dikelabui oleh perubahan format semata. Karena Jaccard Similarity dihitung dari rasio *fingerprint* yang cocok, *partial copying* (menyalin sebagian fungsi/blok kode lalu menulis sisanya secara mandiri) tetap terdeteksi secara **proporsional** — skor mencerminkan porsi yang benar-benar disalin, dan fitur *highlight* menandai persis baris mana yang identik.
- **Pelaporan bertingkat** — alur empat langkah: ringkasan antar-*project* → rincian antar-*file* → inspeksi baris kode dengan sorotan kuning pada bagian yang identik.
- **Visualisasi graf kemiripan** — tampilan jaringan interaktif di mana setiap mahasiswa adalah simpul dan garis menghubungkan pasangan yang melampaui ambang kemiripan yang dapat disetel, sehingga *klaster* mahasiswa yang saling menyalin terlihat seketika — khususnya berguna saat ada puluhan *submission* dalam satu kelas.
- **Export laporan PDF** — unduh laporan ringkasan seluruh pasangan (cocok untuk dokumentasi satu kelas/angkatan), laporan detail satu pasangan project, maupun laporan kode berdampingan dengan *highlight* (format *landscape*, cocok dilampirkan sebagai bukti konkret) — langsung dari antarmuka, tanpa instalasi tambahan.
- **Kategorisasi ambang batas** — hasil persentase dikelompokkan otomatis ke kategori Rendah (`< 30%`), Moderat (`30–80%`), dan Tinggi (`> 80%`).
- **Privasi by design** — tanpa basis data, tanpa penulisan file ke disk; seluruh state hilang begitu sesi berakhir.
- **Teruji & terverifikasi** — 55 *automated test case* yang membandingkan hasil komputasi sistem dengan perhitungan manual (lihat [Pengujian](#pengujian)).

## Arsitektur Sistem

| Layer | Teknologi | Tanggung Jawab |
|---|---|---|
| **Frontend** | Streamlit | *Multi-step wizard* dengan *protected sequential routing* |
| **Backend** | Python (OOP, Service Layer) | Ekstraksi, *preprocessing*, *fingerprinting*, kalkulasi *similarity* |
| **State** | `st.session_state` | "Database" volatil di memori — tanpa persistensi |

Alur navigasi wizard dijaga ketat: pengguna tidak dapat mengakses halaman *Result* tanpa melewati *Comparisons*, atau *Detail* tanpa memilih pasangan *file* di *Result* terlebih dahulu (lihat `app.py::_guard_route`).

```
Home → Upload (.zip) → Comparisons → Result → Detail
                          (Step 1)    (Step 2)  (Step 3)  (Step 4)
```

Dokumentasi arsitektur lebih rinci tersedia di [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Cara Kerja Algoritma

Pipeline analisis terdiri dari lima tahap berurutan:

```
.zip Upload
    │
    ▼
1. Ekstraksi & Filter (.php, .dart, .py)         → services/extractor.py
    │
    ▼
2. Preprocessing (strip komentar → strip whitespace → lowercase)
    │                                              → services/preprocessor.py
    ▼
3. K-Gram + Rolling Hash Rabin-Karp (k=5)         → services/fingerprint.py
    │
    ▼
4. Winnowing Fingerprinting (window=4, SET unik)  → services/fingerprint.py
    │
    ▼
5. Jaccard Similarity + Threshold Categorization  → services/similarity.py
    │
    ▼
Highlight reverse-mapping ke baris asli           → services/highlighter.py
```

**Parameter yang digunakan** (lihat `services/fingerprint.py`):

| Parameter | Nilai | Keterangan |
|---|---|---|
| `k` | 5 | Panjang setiap *k-gram* |
| `w` | 4 | Ukuran *window* Winnowing |
| `base` | 256 | Basis *Rolling Hash Rabin-Karp* |
| `mod` | 1.000.000.007 | Modulus (bilangan prima besar) |

**Threshold kategori** (lihat `services/similarity.py`):

| Rentang | Kategori |
|---|---|
| `< 30%` | Rendah (*Low*) |
| `30% – 80%` | Moderat (*Moderate*) |
| `> 80%` | Tinggi (*High*) |

### Justifikasi Akademik Nilai Threshold

Tidak ada standar tunggal yang mengikat secara universal untuk menentukan batas persentase similarity source code — literatur internasional maupun kebijakan institusi di Indonesia menunjukkan variasi nilai tergantung konteks, *tool*, dan kebijakan kampus. Berikut sumber yang menjadi rujukan penentuan threshold sistem ini:

**Batas bawah 30% (Rendah/Low)** memiliki konsensus luas di literatur Indonesia:
- Kebijakan resmi **S1 Teknologi Informasi, Telkom University Kampus Jakarta** mengategorikan plagiarisme ringan (`< 30%`), sedang (`30–70%`), dan berat (`> 70%`).
- Kebijakan serupa diterapkan **Fakultas Teknik Universitas Pasundan** dan editorial **Jurnal MEDICINUS**.
- Diterapkan secara spesifik pada deteksi plagiarisme *source code* menggunakan algoritma Rabin-Karp, dengan kategori identik (`< 30%` ringan, `30–70%` sedang, `> 70%` besar) — Tugas Akhir dipublikasikan di *Journal of Software Engineering* (ejurnal.seminar-id.com).
- Studi internasional **"Collaboration Versus Cheating"** (Simha, R., et al., arXiv:1812.00276) menetapkan *cut-off* 30% MOSS *similarity* berdasarkan bukti empiris: seluruh kasus ≥30% pernah dirujuk ke tim instruksional, sementara tidak ada kasus <20% yang dirujuk.

**Batas atas 80% (Tinggi/High)** — perlu transparansi: mayoritas sumber Indonesia di atas justru memakai **70%**, bukan 80%, sebagai batas atas. Namun nilai 80% memiliki rujukan langsung yang relevan:
- **Jurnal INOVTEK POLBENG – Seri Informatika** (Politeknik Negeri Bengkalis, terindeks SINTA, ISSN 2527-9866), Vol. 9 No. 1, 2024, "Deteksi Plagiat Tesis Berbahasa Indonesia Menggunakan Metode Cosine Similarity": menetapkan ambang batas 0,8 (80%) — pasangan dokumen dengan kesamaan ≥80% yang diukur lewat metrik Cosine **atau Jaccard** dikategorikan terindikasi plagiat.

**Untuk *source code* secara spesifik**, literatur internasional menunjukkan tidak ada nilai tunggal yang disepakati — beragam *tool* memakai *threshold* optimal yang berbeda-beda:
- **Prechelt & Malpohl (2003)**, *"Finding Plagiarisms Among a Set of Programs with JPlag"*, *Journal of Universal Computer Science*, menerapkan *threshold* 50% untuk hasil JPlag.
- **Cosma & Joy**, dikutip dalam *"Identifying Plagiarised Programming Assignments with Detection Tool Consensus"* (ERIC/files.eric.ed.gov), melaporkan rentang *threshold* optimal yang bervariasi: 40–70% untuk *tool* Sim, 10–70% untuk MOSS, dan 30–70% untuk JPlag.
- **"Detection of a Source Code Plagiarism in a Student Programming Competition"** (arXiv:1912.08138) secara eksplisit menyatakan: *"there is no explicit criterion for what level of similarity can be considered evidence of plagiarism"* — pemilihan *threshold* pada penelitian tersebut diakui bersifat *common sense*, bukan standar baku.

**Kesimpulan untuk thesis/skripsi:** nilai 30%/80% pada sistem ini **dapat dijustifikasi** dengan sumber di atas, tetapi disarankan secara eksplisit didiskusikan di BAB Metodologi sebagai *pilihan desain* (bukan satu-satunya kebenaran), dengan menyitir baik sumber yang mendukung 70% maupun 80% sebagai pembanding — pola penyajian yang umum dan dianggap kuat dalam sidang Tugas Akhir Indonesia. Payung regulasi tertinggi tetap **Peraturan Menteri Pendidikan Nasional RI No. 17 Tahun 2010** tentang Pencegahan dan Penanggulangan Plagiat di Perguruan Tinggi, yang mewajibkan deteksi plagiarisme namun **menyerahkan penentuan nilai ambang batas numerik kepada masing-masing institusi**.

Penjelasan matematis lengkap (formula Rolling Hash, properti Jaccard, strategi *Best Match Only*) tersedia di [`docs/ALGORITHM.md`](docs/ALGORITHM.md).

## Struktur Proyek

```
jinggoplag/
├── app.py                       # Entry point: routing, session_state, dispatch halaman
├── requirements.txt             # Dependensi runtime (streamlit, reportlab)
├── requirements-dev.txt         # Dependensi tambahan untuk testing (pytest, pylint, ruff)
│
├── services/                    # Service Layer (OOP, backend murni, tanpa Streamlit)
│   ├── extractor.py             #   ZipExtractorService — buka .zip, deteksi wrapper folder, filter ekstensi
│   ├── preprocessor.py          #   PreprocessorService — strip komentar, whitespace, case folding, char_map
│   ├── fingerprint.py           #   FingerprintService — K-Gram, Rolling Hash Rabin-Karp, Winnowing
│   ├── similarity.py            #   SimilarityService — Jaccard, Best Match Only, kategorisasi threshold
│   ├── highlighter.py           #   HighlightService — petakan matched hash ke nomor baris asli
│   ├── report_generator.py      #   ReportGeneratorService — export PDF (ringkasan, detail, kode berdampingan)
│   └── graph_service.py         #   GraphService — graf kemiripan (networkx spring layout → SVG interaktif)
│
├── pages/                       # Satu file per halaman wizard
│   ├── home.py                  #   Landing page dengan tombol CTA "ANALYSIS NOW"
│   ├── checker_upload.py        #   Step 1 — upload .zip, jalankan pipeline analisis penuh
│   ├── checker_comparisons.py   #   Step 2 — tabel semua pasangan project, tombol Graf & Export PDF
│   ├── checker_graph.py         #   Step 2 (alternatif) — visualisasi graf jaringan kemiripan
│   ├── checker_result.py        #   Step 3 — breakdown per file dalam satu pasangan, Export PDF detail
│   ├── checker_detail.py        #   Step 4 — kode berdampingan dengan highlight, Export PDF kode
│   └── about.py                 #   Halaman statis: flowchart algoritma, tahapan proses, kredit
│
├── components/                  # Komponen UI yang dipakai ulang lintas halaman
│   ├── navbar.py                 #   Navbar atas: logo, Home/Checker/About, active-state highlighting
│   ├── step_indicator.py         #   Breadcrumb wizard (Step 1-4), dipakai oleh keempat halaman checker
│   └── comparison_table.py       #   Tabel perbandingan generik (badge threshold, ikon view)
│
├── styles/
│   └── main.css                  # Stylesheet global: tema hitam-oranye, sembunyikan chrome Streamlit
│
├── tests/
│   ├── test_parity.py            # 55 automated test — paritas Excel vs sistem (lihat bagian Pengujian)
│   └── fixtures/
│       └── submissions.zip       # Data uji nyata (2 project root, ground truth terverifikasi manual)
│
├── docs/
│   ├── ARCHITECTURE.md           # Keputusan desain, service layer, diagram alur data end-to-end
│   ├── ALGORITHM.md              # Formula matematis: Rolling Hash, Winnowing, Jaccard, threshold
│   └── TESTING.md                # Metodologi pengujian: parity test, black-box scenario, evaluasi akurasi
│
└── .github/workflows/test.yml    # CI — jalankan test otomatis tiap push (matrix Python 3.10/3.11/3.12)
```

## Instalasi & Menjalankan

**Prasyarat:** Python 3.10 atau lebih baru.

```bash
# 1. Clone repository
git clone https://github.com/ipunkdi/jinggoplag.git
cd jinggoplag

# 2. (Opsional tapi disarankan) buat virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi
streamlit run app.py
```

Browser akan terbuka otomatis di `http://localhost:8501`.

## Format Input (.zip)

Struktur arsip yang diharapkan: satu folder per mahasiswa langsung di *root* `.zip`, masing-masing berisi *source code* (boleh bertingkat/*nested*).

```
submissions.zip
├── NamaMahasiswa_A/
│   ├── main.py
│   └── utils.py
├── NamaMahasiswa_B/
│   └── tugas.py
└── NamaMahasiswa_C/
    └── app.py
```

Jika arsip dibuat melalui klik-kanan "Compress to ZIP" pada satu folder induk (sehingga menghasilkan satu folder pembungkus tambahan), sistem akan **mendeteksi dan menghapusnya secara otomatis** (lihat `ZipExtractorService.detect_wrapper_prefix`).

Minimal **dua** *project root* diperlukan agar perbandingan dapat dilakukan.

## Pengujian

Proyek ini dilengkapi *automated test suite* yang memverifikasi setiap tahap pipeline — bukan hanya hasil akhir — terhadap nilai *ground truth* yang sudah diverifikasi manual menggunakan Microsoft Excel (lihat [Verifikasi Akurasi](#verifikasi-akurasi-excel-gold-standard)).

```bash
# Jalankan via Python langsung
python -m tests.test_parity

# Atau via pytest (perlu requirements-dev.txt)
pip install -r requirements-dev.txt
pytest tests/test_parity.py -v
```

Cakupan pengujian (55 *assertion*, 14 kelompok):

| Kelompok | Yang Diverifikasi |
|---|---|
| T1 | Preprocessing — komentar & *whitespace* terhapus, *case folding* benar |
| T2 | Akurasi `char_map` — pemetaan posisi karakter 100% akurat |
| T3 | Rolling Hash == hash naif untuk setiap *k-gram* (properti matematis) |
| T4 | Jumlah *fingerprint* unik sesuai *ground truth* Excel |
| T5 | Intersection, Union, dan Jaccard sesuai *ground truth* Excel |
| T6 | Kategorisasi *threshold* hasil akhir |
| T7 | Batas *threshold* (29.9% → Low, 30.0% → Moderate, dst.) |
| T8 | Cakupan *highlight* — baris yang disorot sesuai *fingerprint* yang cocok |
| T9 | Deteksi *wrapper folder* otomatis pada `.zip` |
| T10 | Penanganan *error* — hanya 1 *project* ditemukan |
| T11 | Penanganan *error* — tidak ada *file* berekstensi yang didukung |
| T12 | *Export* PDF — header `%PDF` valid dan ukuran berkas > 0 byte untuk laporan ringkasan & detail |
| T13 | *Export* PDF kode berdampingan (*landscape*) — header `%PDF` valid dan ukuran berkas > 0 byte untuk laporan kode dengan *highlight* |
| T14 | Visualisasi Graf — `GraphService` menghasilkan NetworkX Graph, statistik, dan SVG valid (ada `<circle>` dan `</svg>`) dari hasil nyata; graf kosong tidak *crash* |

Detail metodologi pengujian (termasuk *black-box testing* alur UI) ada di [`docs/TESTING.md`](docs/TESTING.md).

## Verifikasi Akurasi (Excel Gold Standard)

Karena sistem ini adalah instrumen deteksi langsung tanpa proses *training* atau dataset berlabel, validitasnya diuji dengan **membandingkan hasil komputasi sistem terhadap simulasi manual** menggunakan Microsoft Excel — setiap tahap (K-Gram, Hashing, Winnowing, Jaccard) dihitung ulang baris-per-baris menggunakan formula Excel native (`MID`, `CODE`, `MOD`, `COUNTIF`), independen dari kode Python.

Hasil pada sampel uji (`tests/fixtures/submissions.zip`):

| Komponen | Nilai |
|---|---|
| `\|Fingerprint Project A\|` | 194 |
| `\|Fingerprint Project B\|` | 200 |
| Intersection | 106 |
| Union | 288 |
| **Jaccard Similarity** | **36.8056%** |
| Kategori | Moderat |

Sistem menghasilkan nilai yang **identik** dengan simulasi Excel ini — dikonfirmasi otomatis lewat `tests/test_parity.py` (T4, T5).

## Keterbatasan yang Diketahui

Demi transparansi akademik, berikut batasan yang disadari dan didokumentasikan secara sengaja:

- **Rentan terhadap penggantian nama secara masif.** Pendekatan *lexical fingerprinting* (bukan *AST-based*) berarti jika *seluruh* nama variabel/fungsi/kelas diganti secara konsisten, *fingerprint* akan sangat berbeda meski logika program identik.
- **Tidak mendeteksi kemiripan logika lintas bahasa.** Kode PHP dan Python yang identik secara logika tidak terdeteksi mirip karena sintaks berbeda total.
- **Karakter Unicode di luar *Basic Multilingual Plane*** (mis. emoji tertentu) dapat menghasilkan hasil yang sedikit berbeda antara Python (yang menghitung *code point*) dan Excel (yang menghitung *surrogate pair* UTF-16) — perbedaan ini bersifat *edge case* dan berdampak pada skala desimal yang sangat kecil terhadap hasil akhir.

## Kontribusi

Lihat [`CONTRIBUTING.md`](CONTRIBUTING.md) untuk panduan kontribusi, *coding style*, dan langkah menjalankan *test* sebelum mengajukan *pull request*.

## Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).

## Kredit

**Pengembang:** Dafa Ifaldi
**Institusi:** Politeknik Negeri Banyuwangi
**Konteks:** Tugas Akhir — Sistem Deteksi Plagiarisme Source Code Berbasis Web Menggunakan Algoritma Winnowing Fingerprinting dengan Rolling Hash Rabin-Karp
