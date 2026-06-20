# Algoritma: Penjelasan Matematis

Dokumen ini menjelaskan formula dan properti matematis dari setiap tahap algoritma yang diimplementasikan di `services/fingerprint.py` dan `services/similarity.py`. Disusun agar dapat langsung dirujuk dalam penulisan akademik (skripsi/tugas akhir).

## 1. Preprocessing

Tiga transformasi berurutan diterapkan pada *source code* mentah sebelum analisis (`services/preprocessor.py`):

1. **Penghapusan komentar** — *bahasa-spesifik* (regex yang membedakan komentar dari string literal, sehingga `"text # bukan komentar"` tidak ikut terpotong).
2. **Penghapusan whitespace** — seluruh spasi, tab, dan baris baru dihapus total (bukan di-*collapse* menjadi satu spasi), sesuai metodologi yang juga digunakan dalam perhitungan manual Excel.
3. **Case folding** — seluruh karakter diubah ke huruf kecil.

## 2. K-Gram (Shingling)

Teks yang telah diproses dipecah menjadi substring tumpang-tindih sepanjang `k` karakter (*sliding window*):

$$
\text{kgram}_i = \text{processed}[i \ldots i+k-1], \quad i = 0, 1, \ldots, n-k
$$

dengan `n` adalah panjang teks setelah *preprocessing* dan `k = 5` (dikonfirmasi sebagai parameter sistem).

## 3. Rolling Hash Rabin-Karp (Standar)

Setiap *k-gram* dihitung nilai hash-nya menggunakan *Rolling Hash Rabin-Karp standar*, yang menjamin kompleksitas waktu **O(n)** untuk seluruh teks (bukan O(n·k) seperti penghitungan naif per *k-gram*).

**Hash pertama** (polinomial naif):

$$
H_0 = \sum_{j=0}^{k-1} \text{ord}(s_j) \cdot \text{BASE}^{\,k-1-j} \pmod{\text{MOD}}
$$

**Hash berikutnya** (*rolling update*, O(1) per langkah):

$$
H_i = \Bigl(\bigl(H_{i-1} - \text{ord}(s_{i-1}) \cdot \text{BASE}^{\,k-1}\bigr) \cdot \text{BASE} + \text{ord}(s_{i+k-1})\Bigr) \pmod{\text{MOD}}
$$

dengan:
- `BASE = 256` — basis numerik (mengakomodasi seluruh nilai byte ASCII/Latin-1)
- `MOD = 1.000.000.007` — modulus, bilangan prima besar untuk meminimalkan kolisi hash
- $s_{i-1}$ — karakter yang **keluar** dari *window* (kiri)
- $s_{i+k-1}$ — karakter yang **masuk** ke *window* (kanan, posisi baru)

**Properti yang dijamin dan diverifikasi** (`tests/test_parity.py`, T3):

$$
H_i = \text{poly\_hash}(\text{processed}[i \ldots i+k-1]) \quad \text{untuk semua } i
$$

Artinya nilai *rolling hash* identik dengan nilai hash yang dihitung secara naif untuk *k-gram* yang sama — properti ini dibuktikan langsung lewat pengujian otomatis, bukan diasumsikan.

## 4. Winnowing Fingerprinting

Dari deretan nilai hash $H_0, H_1, \ldots, H_{n-k}$, algoritma Winnowing memilih subset yang merepresentasikan *fingerprint* dokumen, dengan dua aturan:

1. **Window minimum**: untuk setiap *window* sepanjang `w = 4` hash berurutan, pilih nilai **minimum**.
2. **Tie-breaking rightmost**: jika ada beberapa nilai minimum yang sama dalam satu *window*, pilih yang berada di posisi **paling kanan** — menghasilkan *fingerprint* yang lebih stabil terhadap penyisipan/penghapusan kode di bagian awal teks.
3. **Deduplikasi berurutan**: jika *window* yang bergeser menghasilkan posisi minimum yang **sama** dengan *window* sebelumnya, tidak ditambahkan duplikat.

**Fingerprint akhir adalah SET (himpunan) unik** dari seluruh nilai minimum yang terpilih — setiap nilai hash hanya dihitung **satu kali** meskipun muncul di banyak *window* berbeda. Ini adalah poin krusial: kesalahan paling umum dalam implementasi Winnowing adalah menganggap *fingerprint* sebagai *multiset* (dengan duplikat), yang membuat metrik Jaccard berikutnya menjadi tidak valid secara matematis.

## 5. Jaccard Similarity

Diberikan dua *fingerprint set* $F_A$ dan $F_B$ dari dua *file* yang dibandingkan:

$$
J(F_A, F_B) = \frac{|F_A \cap F_B|}{|F_A \cup F_B|}
$$

dengan:

$$
|F_A \cup F_B| = |F_A| + |F_B| - |F_A \cap F_B| \quad \text{(prinsip inklusi-eksklusi)}
$$

Hasil dikonversi ke persentase: $\text{Similarity}(\%) = J(F_A, F_B) \times 100$.

### Strategi Pencocokan File: Best Match Only

Ketika membandingkan dua *project* yang masing-masing berisi banyak *file*, setiap *file* di Project A dipasangkan dengan **satu** *file* di Project B yang menghasilkan skor Jaccard **tertinggi** (`SimilarityService._compare_projects`). Skor *project-level* adalah rata-rata dari seluruh skor pasangan *file* terbaik tersebut.

### Kategorisasi Threshold

$$
\text{Kategori} =
\begin{cases}
\text{Rendah (Low)} & \text{jika } \text{Similarity} < 30\% \\
\text{Moderat (Moderate)} & \text{jika } 30\% \le \text{Similarity} \le 80\% \\
\text{Tinggi (High)} & \text{jika } \text{Similarity} > 80\%
\end{cases}
$$

## 6. Highlight Reverse Mapping

Untuk menampilkan baris kode yang identik di UI, `HighlightService` memetakan kembali setiap `matched_hash` ke rentang karakter di teks asli (menggunakan `char_map`, lihat [`ARCHITECTURE.md`](ARCHITECTURE.md)), lalu mengonversi rentang karakter tersebut ke nomor baris menggunakan peta `char_to_line` yang dibangun dari posisi karakter `\n` di teks asli.

## Verifikasi Independen

Seluruh formula di atas diverifikasi **dua kali secara independen**:

1. **Implementasi Python** (`services/fingerprint.py`, `services/similarity.py`)
2. **Simulasi manual Microsoft Excel** — setiap baris dihitung ulang menggunakan formula Excel native (`MID`, `CODE`, `MOD`, `MIN`, `COUNTIF`) tanpa bergantung pada kode Python sama sekali.

Kedua pendekatan menghasilkan nilai yang **identik** pada data uji (lihat [README — Verifikasi Akurasi](../README.md#verifikasi-akurasi-excel-gold-standard)), memberikan bukti validitas implementasi yang independen dari satu sumber kebenaran tunggal.
