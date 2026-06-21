# Arsitektur Sistem

Dokumen ini menjelaskan keputusan desain arsitektural Jinggo Plag secara rinci, ditujukan bagi peninjau (dosen penguji) atau pengembang lain yang ingin memahami atau melanjutkan proyek ini.

## Prinsip Desain

1. **Separation of Concerns** — logika algoritma (Service Layer) sepenuhnya terpisah dari logika presentasi (Streamlit UI). Setiap *service* dapat diuji, dipanggil, dan diverifikasi tanpa menjalankan satu baris kode UI apa pun — terbukti dari `tests/test_parity.py` yang memanggil seluruh *service* secara langsung.
2. **Stateless Backend, Stateful Session** — *service* tidak menyimpan state internal antar pemanggilan (semua method menerima input dan mengembalikan output baru). State aplikasi (hasil analisis, navigasi) hidup sepenuhnya di `st.session_state`, dikelola terpusat oleh `app.py`.
3. **Privacy by Design** — tidak ada operasi tulis ke *filesystem* server di mana pun dalam *codebase*. Pencarian `open(..., "w")` di seluruh `services/` dan `pages/` akan menghasilkan nol kecocokan.
4. **Fail Loud, Fail Early** — kegagalan (`.zip` rusak, ekstensi tidak didukung, hanya 1 *project*) dilempar sebagai `ValueError` dengan pesan yang dapat dibaca pengguna langsung di tahap ekstraksi, bukan dibiarkan merambat menjadi *exception* generik yang membingungkan di tahap selanjutnya.

## Lapisan Service (`services/`)

| Service | Input | Output | Tidak Bergantung Pada |
|---|---|---|---|
| `ZipExtractorService` | `bytes` arsip `.zip` | `dict[project][file] -> source code` | Streamlit, *service* lain |
| `PreprocessorService` | `str` *source code* mentah + ekstensi | `PreprocessedFile` (original, processed, language, char_map) | Streamlit, *service* lain |
| `FingerprintService` | `processed_text` + `char_map` | `FingerprintResult` (fingerprints, hash_positions) | Streamlit, *service* lain |
| `SimilarityService` | `dict[project][file] -> FingerprintResult` | `list[ComparisonResult]` | Streamlit, *service* lain |
| `HighlightService` | `original_text` + `hash_positions` + `matched_hashes` | `list[HighlightedLine]` | Streamlit, *service* lain |
| `ReportGeneratorService` | `list[ComparisonResult]`, satu `ComparisonResult`, atau (`ComparisonResult` + `FilePairResult` + 2× `list[HighlightedLine]`) | `bytes` PDF | Streamlit, *service* lain |

Lima *service* pertama (`ZipExtractorService` s.d. `HighlightService`) membentuk **pipeline deteksi inti** yang berurutan — dipanggil langsung saat analisis berjalan (lihat diagram di bawah). `ReportGeneratorService` **bukan bagian dari pipeline inti**; ia adalah *service* presentasi yang dipanggil *on-demand* dari `pages/checker_comparisons.py` dan `pages/checker_result.py` saat pengguna menekan tombol *Export PDF*, mengonsumsi *output* yang sudah ada (`ComparisonResult`) tanpa melakukan komputasi *similarity* baru. Pemisahan ini sengaja dijaga agar logika algoritma deteksi tetap terisolasi dari logika *output*/pelaporan.

Setiap *service* adalah kelas independen tanpa *dependency* satu sama lain secara langsung — orkestrasi pipeline inti (memanggil lima *service* deteksi secara berurutan) dilakukan oleh `pages/checker_upload.py::_run_pipeline_steps`, BUKAN oleh *service* itu sendiri. Ini memungkinkan setiap *service* diuji dalam isolasi penuh.

### Mengapa `char_map`, Bukan Pencarian Posisi?

Versi awal sistem menggunakan `str.find()` untuk menebak posisi *k-gram* di teks asli (sebelum *preprocessing*) — pendekatan ini tidak akurat untuk *k-gram* yang muncul berulang.

Solusi final: `PreprocessorService` membangun `char_map`, sebuah `list[int]` di mana `char_map[i]` adalah posisi karakter ke-`i` dari `processed` text di dalam `original` text. Properti yang dijamin secara matematis:

```python
original.lower()[char_map[i]] == processed[i]   # untuk semua i
```

Dibangun dengan algoritma *two-pointer* `O(n+m)` di `PreprocessorService._build_char_map()`. `FingerprintService` lalu memetakan rentang *k-gram* `processed[p:p+k]` langsung ke `original[char_map[p] : char_map[p+k-1]+1]` — akurat 100%, tanpa ambiguitas, tanpa pencarian.

## Lapisan UI (`pages/`, `components/`)

### Protected Sequential Routing

`app.py::_guard_route()` memverifikasi data *upstream* tersedia di `session_state` sebelum mengizinkan akses ke suatu *route*:

```python
ROUTE_RESULT   → butuh comparison_results & selected_comparison
ROUTE_DETAIL   → butuh comparison_results & selected_comparison & selected_file_pair
```

Jika data belum tersedia (misalnya pengguna mengetik URL langsung atau navigasi non-linear), pengguna otomatis diarahkan kembali ke *route* terdekat yang valid — bukan ditampilkan halaman kosong atau *crash*.

### Mengapa `set_page_config()` Dipanggil di Dalam `main()`?

Streamlit mewajibkan `set_page_config()` menjadi *Streamlit command* **pertama yang dieksekusi** pada setiap *run* skrip. Karena tidak ada satu pun modul `pages/*` atau `components/*` yang mengeksekusi `st.*` pada level modul (hanya mendefinisikan fungsi `render()`), aman untuk menaruh seluruh `import` secara konvensional di atas `app.py`, dan memanggil `set_page_config()` sebagai baris pertama di dalam `main()` — menghasilkan urutan *import* yang bersih sesuai PEP 8 tanpa mengorbankan *requirement* Streamlit.

### Catatan CSS — Menghindari Class Auto-Generated

`styles/main.css` secara sengaja **tidak** menggunakan selector `.st-emotion-cache-xxxxx` di manapun. Class tersebut di-*generate* otomatis oleh *Emotion* (CSS-in-JS internal Streamlit) dan dapat berubah tanpa peringatan antar versi Streamlit. Seluruh *override* tampilan menggunakan selector `data-testid` resmi (`stAppViewContainer`, `stHeader`, `stButton`, dll.) yang merupakan kontrak stabil dari komponen Streamlit.

## Diagram Alur Data End-to-End

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   .zip      │────▶│ ZipExtractorService│───▶│ projects_raw     │
│  (upload)   │     └──────────────────┘     │ {proj:{file:src}} │
└─────────────┘                              └────────┬─────────┘
                                                        │
                     ┌──────────────────────┐          ▼
                     │ PreprocessorService   │◀─────────┘
                     │ (per file)             │
                     └───────────┬────────────┘
                                  ▼
                     PreprocessedFile{original, processed,
                                       language, char_map}
                                  │
                     ┌────────────▼───────────┐
                     │  FingerprintService     │
                     │  (K-Gram→Hash→Winnowing)│
                     └────────────┬────────────┘
                                  ▼
                     FingerprintResult{fingerprints, hash_positions}
                                  │
                     ┌────────────▼───────────┐
                     │  SimilarityService       │
                     │  (Jaccard, Best Match)   │
                     └────────────┬────────────┘
                                  ▼
                     list[ComparisonResult] → session_state
                                  │
            ┌─────────────────────┼─────────────────────┐
            │ (klik Export PDF     │ (pengguna memilih    │ (klik Export PDF
            │  di Comparisons)     │  pasangan)            │  di Result)
            ▼                     │                       ▼
 ┌───────────────────────┐        │          ┌───────────────────────┐
 │ ReportGeneratorService  │        │          │ ReportGeneratorService  │
 │ .generate_summary_      │        │          │ .generate_detail_       │
 │  report()                │        │          │  report()                │
 └────────────┬────────────┘        │          └────────────┬────────────┘
              ▼                     ▼                       ▼
      bytes PDF                ┌────────────────────────┐   bytes PDF
      → download_button        │   HighlightService       │   → download_button
                                │   (char pos → baris)     │
                                └────────────┬────────────┘
                                             ▼
                              list[HighlightedLine] → render Detail page
                                             │
                                             │ (klik Export PDF di Detail)
                                             ▼
                              ┌────────────────────────────┐
                              │  ReportGeneratorService       │
                              │  .generate_code_comparison_   │
                              │   report() — landscape, 2 kolom│
                              └────────────────┬───────────────┘
                                               ▼
                                       bytes PDF → download_button
```

`ReportGeneratorService` dipanggil pada **tiga titik berbeda**, semuanya *on-demand* (tidak pernah otomatis saat analisis berjalan):

1. **Halaman Comparisons** → `generate_summary_report(list[ComparisonResult])` — laporan seluruh pasangan.
2. **Halaman Result** → `generate_detail_report(ComparisonResult)` — laporan satu pasangan project, breakdown per file.
3. **Halaman Detail** → `generate_code_comparison_report(comparison, file_pair, highlighted_a, highlighted_b)` — **berbeda dari dua titik lainnya**: method ini dipanggil *setelah* `HighlightService` selesai, karena ia butuh `list[HighlightedLine]` sebagai input, bukan langsung dari `ComparisonResult`. Inilah satu-satunya titik di mana `ReportGeneratorService` berada di hilir `HighlightService`, bukan paralel terhadapnya.
