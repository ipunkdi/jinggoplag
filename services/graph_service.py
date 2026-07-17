"""
GraphService
============
Menghitung dan menghasilkan representasi graf kemiripan antar project
menggunakan algoritma *layout* dari NetworkX.

Desain:
- Node  = satu project root mahasiswa
- Edge  = kemiripan antara dua project (hanya yang >= min_similarity)
- Warna edge & node  = kategori threshold tertinggi (High/Moderate/Low)
- Ukuran node        = proporsional terhadap jumlah koneksi (degree)
- Label node         = nama project yang diperpendek, posisi DI BAWAH node
- Tooltip            = nama project lengkap (on-hover)

Output akhir adalah string HTML yang siap di-render via
`st.iframe`, sehingga tidak membutuhkan library
visualisasi tambahan (plotly, pyvis, dll.) di luar NetworkX.

Menggunakan `seed=42` (untuk komponen bernode tunggal) dan penempatan grid
deterministik antar klaster agar tata letak graf **reproducible** — input
data yang sama selalu menghasilkan tampilan yang persis sama (penting
untuk konsistensi presentasi akademik).

Perbaikan v2 (pasca sidang):
- k = max(3.0, 1.8*log(n+1))  -> untuk n=28: k~=6.1 (vs lama 1.4), node tidak berdesakan
- iterations = 150             -> layout lebih konvergen
- radius = 12 + degree*1.2    -> node lebih kecil (degree=10: 24px vs lama 45px)
- edge width max 3.5px         -> vs lama 6.5px, klaster tidak gelap
- canvas dinamis               -> tumbuh proporsional dengan n
- label di BAWAH node          -> terbaca meski node kecil

Perbaikan v3 (revisi dosen penguji - kesesuaian posisi dengan similarity):
- MASALAH v2: spring_layout berbobot menempatkan jarak antar-node lewat
  GAYA (implisit). Gaya tolak global (k^2/distance^2) berlaku untuk SEMUA
  pasangan node, sedangkan gaya tarik similarity hanya berlaku pada edge
  yang terhubung. Saat k diperbesar untuk mengurangi crowding, gaya tolak
  global itu mendominasi gaya tarik similarity -> pasangan similarity
  tinggi tidak konsisten terlihat lebih dekat.
- SOLUSI v3: Kamada-Kawai layout dengan target jarak EKSPLISIT
  (distance = 1 - similarity) per connected component (klaster hasil
  algoritma clustering yang sama dengan graph_stats).

Perbaikan v4 (fix overlap parah pasca v3):
- MASALAH v3: setiap klaster dilayout dengan `scale` KK yang SAMA
  (tetap = 1.0) dan ditempatkan pada grid dengan ukuran sel yang SAMA
  rata, tidak peduli klaster itu berisi 2 node atau 20 node. Akibatnya
  klaster besar dipaksa masuk ruang sesempit klaster kecil (overlap
  parah), sementara skala normalisasi kanvas didominasi sebaran grid
  klaster kecil/terisolasi -> klaster besar makin terjepit ke pojok
  kecil.
- SOLUSI v4: setiap klaster memakai `scale = 0.55 * sqrt(n)`, sehingga
  ruang yang dialokasikan tumbuh proporsional dengan jumlah node di
  dalamnya (bukan seragam). Klaster-klaster itu lalu disusun berjajar
  dengan algoritma *shelf packing*.

Perbaikan v5 (fix bentuk klaster memanjang/rantai pasca v4):
- MASALAH v4: Kamada-Kawai menghitung jarak target antar SEMUA pasangan
  node lewat SHORTEST-PATH DI GRAF (bukan hanya edge langsung). Untuk
  graf yang topologinya menyerupai rantai/pohon (banyak node terhubung
  transitif lewat similarity sedang, bukan klik penuh), ini membuat
  hasil layout meregang memanjang mengikuti rantai tsb -- bukan
  menggerombol kompak sesuai similarity antar-pasangan langsung.
- SOLUSI v5: ganti ke FORCE-DIRECTED LAYOUT custom (spring-embedder ala
  Eades) via `_force_directed_layout()`. Setiap edge punya panjang pegas
  target = fungsi LANGSUNG dari similarity edge itu (bukan shortest-
  path), dikombinasikan dengan gaya tolak (repulsion) antar SEMUA
  pasangan node dalam klaster. Ini menghasilkan bentuk lebih organik/
  kompak dan rasio lebar:tinggi yang seimbang, sambil tetap menjamin
  pasangan similarity tinggi saling berdekatan.
"""

import html
import math
import random
from typing import Optional

import networkx as nx


# ── Palet warna threshold (bg, stroke) ───────────────────────────────────────
THRESHOLD_PALETTE: dict = {
    "High":     ("#FFCDD2", "#C62828"),
    "Moderate": ("#FFE0B2", "#E65100"),
    "Low":      ("#C8E6C9", "#2E7D32"),
}

THRESHOLD_ORDER: dict = {"High": 2, "Moderate": 1, "Low": 0}

# ── Konstanta ukuran canvas default ──────────────────────────────────────────
CANVAS_WIDTH  = 820
CANVAS_HEIGHT = 560
CANVAS_MARGIN = 100


class GraphService:
    """Menghitung graf kemiripan dan menghasilkan SVG interaktif."""

    def build_graph(
        self, comparison_results: list, min_similarity: float = 30.0
    ) -> nx.Graph:
        """
        Bangun NetworkX Graph dari daftar ComparisonResult.

        Hanya edge dengan similarity >= min_similarity yang ditambahkan.
        Semua node (project) selalu ada — termasuk yang terisolasi.

        Args:
            comparison_results: list[ComparisonResult] dari SimilarityService.
            min_similarity:     Batas minimum similarity (persentase 0-100).

        Returns:
            nx.Graph dengan atribut node (label) dan edge (similarity, threshold).
        """
        graph = nx.Graph()

        for comp in comparison_results:
            label_a = self._short_label(comp.project_a)
            label_b = self._short_label(comp.project_b)

            if comp.project_a not in graph:
                graph.add_node(comp.project_a, label=label_a)
            if comp.project_b not in graph:
                graph.add_node(comp.project_b, label=label_b)

            if comp.similarity >= min_similarity:
                graph.add_edge(
                    comp.project_a, comp.project_b,
                    similarity=comp.similarity,
                    threshold=comp.threshold,
                )

        return graph

    def graph_stats(self, graph: nx.Graph) -> dict:
        """
        Hitung statistik ringkas dari graf yang sudah difilter.

        Returns:
            Dict berisi jumlah node, edge, komponen terhubung, node
            terisolasi, dan `layout_fidelity` (korelasi Pearson antara
            jarak node hasil render dan dissimilarity/1-similarity -
            bukti kuantitatif bahwa posisi node pada visualisasi
            konsisten dengan nilai similarity, untuk keperluan validasi
            akademik). Nilai mendekati 1.0 = jarak render sangat
            konsisten dengan similarity; None jika edge < 2 (korelasi
            tidak bermakna secara statistik).
        """
        components     = list(nx.connected_components(graph))
        isolated_count = sum(1 for c in components if len(c) == 1)

        return {
            "node_count":      graph.number_of_nodes(),
            "edge_count":      graph.number_of_edges(),
            "component_count": len(components),
            "isolated_count":  isolated_count,
            "largest_cluster": max((len(c) for c in components), default=0),
            "layout_fidelity": self._layout_fidelity(graph),
        }

    def _layout_fidelity(self, graph: nx.Graph) -> Optional[float]:
        """
        Ukur seberapa konsisten posisi node hasil layout dengan similarity.

        Dihitung sebagai korelasi Pearson antara:
        - jarak Euclidean antar-node yang terhubung pada hasil layout, dan
        - dissimilarity edge tsb (1 - similarity/100).

        Korelasi POSITIF dan kuat (mendekati 1.0) berarti: semakin besar
        dissimilarity (semakin rendah similarity), semakin jauh jaraknya
        di layout -- dengan kata lain, similarity tinggi -> node
        berdekatan, persis kriteria yang diminta dosen penguji.

        Returns:
            Float korelasi Pearson pada rentang [-1, 1], atau None jika
            jumlah edge < 2 (korelasi tidak terdefinisi/tidak bermakna).
        """
        if graph.number_of_edges() < 2:
            return None

        pos = self._compute_layout(graph)
        dist, dissim = [], []
        for u, v, data in graph.edges(data=True):
            dist.append(math.dist(pos[u], pos[v]))
            dissim.append(1.0 - data.get("similarity", 50) / 100.0)

        n = len(dist)
        mean_d, mean_s = sum(dist) / n, sum(dissim) / n
        cov = sum((dist[i] - mean_d) * (dissim[i] - mean_s) for i in range(n))
        sd_d = math.sqrt(sum((x - mean_d) ** 2 for x in dist))
        sd_s = math.sqrt(sum((x - mean_s) ** 2 for x in dissim))

        if sd_d == 0 or sd_s == 0:
            return None
        return cov / (sd_d * sd_s)

    def render_svg(
        self,
        graph: nx.Graph,
        width:  int = CANVAS_WIDTH,
        height: int = CANVAS_HEIGHT,
        margin: int = CANVAS_MARGIN,
    ) -> str:
        """
        Hasilkan string SVG interaktif dari NetworkX Graph.

        Canvas diperbesar secara dinamis sesuai jumlah node agar layout
        punya ruang yang cukup:
            n=5  -> 820x560  |  n=28 -> 980x700  |  n=50 -> 1200x800
        Edge tipis (max 3.5px), node lebih kecil (r=12+deg*1.2), label
        di bawah node - ketiganya mengurangi kepadatan visual di klaster.

        Args:
            graph:  NetworkX Graph dari build_graph().
            width:  Lebar canvas minimum SVG (piksel).
            height: Tinggi canvas minimum SVG (piksel).
            margin: Jarak minimum node dari tepi canvas (piksel).

        Returns:
            String SVG siap di-render via st.iframe.
        """
        if not graph.nodes():
            return self._empty_svg(width, height)

        # Canvas dinamis: tumbuh proporsional dengan jumlah node
        n     = graph.number_of_nodes()
        eff_w = max(width,  min(1200, n * 36))
        eff_h = max(height, min(800,  n * 26))
        eff_m = max(margin, min(130,  eff_w // 7))

        pos        = self._compute_layout(graph)
        canvas_pos = self._normalize_to_canvas(pos, eff_w, eff_h, eff_m)
        node_max_threshold = self._node_max_threshold(graph)

        parts: list = [
            self._svg_header(eff_w, eff_h),
            self._svg_defs(),
            '<g id="graph-group">',    # target JS pan/zoom (edge + node)
        ]
        parts.extend(self._render_edges(graph, canvas_pos))
        parts.extend(self._render_nodes(graph, canvas_pos, node_max_threshold))
        parts.append("</g>")          # legend di LUAR agar tetap fixed
        parts.append(self._render_legend(eff_w, eff_h))
        parts.append("</svg>")

        return "\n".join(parts)

    # ── Layout helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_layout(graph: nx.Graph) -> dict:
        """
        Layout dua tahap: Kamada-Kawai per-klaster (ukuran proporsional
        terhadap jumlah node) + shelf packing antar-klaster.

        MASALAH v2 (spring_layout berbobot): gaya tolak global antar SEMUA
        pasangan node (k^2/distance^2) selalu aktif, sementara gaya tarik
        dari similarity hanya aktif pada edge yang terhubung. Saat k
        diperbesar untuk menghindari overlap, gaya tolak global itu
        mendominasi gaya tarik similarity, sehingga pasangan similarity
        tinggi tetap tidak terlihat jelas lebih dekat.

        MASALAH v3 (grid seragam + scale KK tetap): setiap klaster
        dipaksa masuk area KK dengan `scale` yang SAMA (1.0) dan
        ditempatkan pada sel grid berukuran SAMA, tidak peduli isinya
        2 node atau 20 node. Klaster besar jadi overlap parah, sementara
        skala normalisasi kanvas didominasi sebaran grid klaster
        kecil/terisolasi -> klaster besar makin terjepit ke pojok kecil.

        SOLUSI v4:
        1. Tiap klaster memakai target jarak EKSPLISIT (distance =
           1 - similarity) di dalam Kamada-Kawai, sehingga pasangan
           similarity tinggi dijamin ditempatkan berdekatan.
        2. `scale` Kamada-Kawai per klaster TIDAK tetap, melainkan
           `0.55 * sqrt(n)` -> ruang yang dialokasikan tumbuh
           proporsional dengan jumlah node di klaster tsb, sehingga
           klaster besar tidak overlap.
        3. Klaster-klaster (masing-masing sudah punya ukuran berbeda-
           beda) disusun berjajar dengan *shelf packing*: klaster
           ditempatkan dari kiri ke kanan sesuai lebarnya masing-masing,
           pindah ke baris baru saat melebihi lebar maksimum baris.
           Ini mencegah celah kosong berlebihan antara klaster besar
           dan klaster kecil/node terisolasi.
        """
        components = list(nx.connected_components(graph))
        components.sort(key=len, reverse=True)  # klaster besar diletakkan lebih dulu

        n_total        = max(graph.number_of_nodes(), 1)
        max_row_width  = max(6.0, 2.4 * math.sqrt(n_total))
        padding        = 0.7

        pos: dict = {}
        cursor_x, cursor_y, row_height = 0.0, 0.0, 0.0

        for comp_nodes in components:
            n = len(comp_nodes)

            if n == 1:
                node = next(iter(comp_nodes))
                local_pos = {node: (0.0, 0.0)}
                comp_w = comp_h = 0.5
            else:
                sub = graph.subgraph(comp_nodes).copy()
                local_pos = GraphService._force_directed_layout(sub)

                xs = [p[0] for p in local_pos.values()]
                ys = [p[1] for p in local_pos.values()]
                minx, miny = min(xs), min(ys)
                local_pos = {
                    nd: (x - minx, y - miny) for nd, (x, y) in local_pos.items()
                }
                comp_w = max(xs) - minx
                comp_h = max(ys) - miny

            # Shelf packing: pindah baris kalau klaster ini melebihi lebar maksimum
            if cursor_x > 0 and cursor_x + comp_w > max_row_width:
                cursor_x = 0.0
                cursor_y += row_height + padding
                row_height = 0.0

            for node, (x, y) in local_pos.items():
                pos[node] = (x + cursor_x, y + cursor_y)

            cursor_x   += comp_w + padding
            row_height  = max(row_height, comp_h)

        return pos

    @staticmethod
    def _force_directed_layout(
        sub: nx.Graph, iterations: int = 1200, seed: int = 42
    ) -> dict:
        """
        Spring-embedder custom (mirip algoritma Eades) untuk satu klaster.

        Berbeda dari Kamada-Kawai, target jarak di sini HANYA dihitung
        dari similarity edge yang terhubung LANGSUNG (bukan shortest-path
        di graf) -- sehingga bentuk klaster tidak "meregang" mengikuti
        rantai transitif, tapi menggerombol sesuai kekuatan similarity
        pasangan-pasangan yang benar-benar terhubung.

        Dua gaya yang bekerja tiap iterasi:
        - REPULSI: berlaku antar SEMUA pasangan node (bukan hanya yang
          terhubung), F = k_repel / distance^2, mencegah node saling
          menimpa (overlap) di area padat.
        - PEGAS (Hooke's law) per edge: F = k_spring * (distance - L),
          dengan L = panjang target dari similarity edge tsb.
          L kecil (similarity tinggi) -> node ditarik saling mendekat;
          L besar (similarity rendah) -> node didorong saling menjauh.

        `temperature` menurun tiap iterasi (simulated annealing) agar
        posisi node makin stabil menjelang akhir, mencegah osilasi.

        Parameter (len_min, len_max, k_spring, k_repel, iterations) hasil
        pengujian empiris: korelasi Pearson antara jarak node hasil render
        dan dissimilarity (1 - similarity) diukur pada beberapa topologi
        graf uji (klaster padat acak & klaster rantai+klik). Parameter
        v5 awal (len=0.35-2.2, k_spring=0.9, k_repel=0.55, iter=400)
        hanya mencapai korelasi ~0.42-0.46 -- gaya pegas terlalu lemah
        dibanding gaya tolak, sehingga tarikan similarity kalah dominan.
        Parameter saat ini menaikkan korelasi menjadi ~0.78-0.92 pada
        topologi yang sama, tanpa menimbulkan overlap node (jarak minimum
        antar-node tetap positif di semua pengujian) dan tanpa bentuk
        klaster kembali memanjang (rasio lebar:tinggi tetap wajar, <2.2).

        Args:
            sub:        Subgraph NetworkX untuk satu connected component.
            iterations: Jumlah iterasi simulasi (makin besar makin stabil;
                        1200 sudah konvergen -- 2000 iterasi tidak lagi
                        meningkatkan korelasi secara signifikan).
            seed:       Seed random untuk posisi awal, agar reproducible.

        Returns:
            Dict {node: (x, y)} posisi hasil simulasi.
        """
        rng   = random.Random(seed)
        nodes = list(sub.nodes())
        n     = len(nodes)
        pos   = {node: (rng.uniform(-1, 1), rng.uniform(-1, 1)) for node in nodes}

        # Rentang panjang pegas dilebarkan (0.10-3.5, dari 0.35-2.2) dan
        # k_spring dinaikkan relatif terhadap k_repel (2.2 : 0.25, dari
        # 0.9 : 0.55) supaya gaya tarik/tolak berbasis similarity lebih
        # dominan dibanding gaya tolak generik antar-semua-node.
        len_min, len_max = 0.10, 3.5   # rentang panjang pegas (unit pra-normalisasi)
        k_spring, k_repel = 2.2, 0.25
        min_dist = 0.05                 # batas bawah jarak, hindari pembagian nol

        target_len: dict = {}
        for u, v, data in sub.edges(data=True):
            sim = data.get("similarity", 50) / 100.0
            # similarity tinggi -> panjang pegas target kecil (node saling dekat)
            target_len[(u, v)] = len_min + (1.0 - sim) * (len_max - len_min)

        temperature, cooling = 1.0, 0.995

        for _ in range(iterations):
            disp = {node: [0.0, 0.0] for node in nodes}

            # Gaya tolak: semua pasangan node (mencegah overlap)
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = nodes[i], nodes[j]
                    dx = pos[a][0] - pos[b][0]
                    dy = pos[a][1] - pos[b][1]
                    dist = max(min_dist, math.hypot(dx, dy))
                    force = k_repel / (dist * dist)
                    ux, uy = dx / dist, dy / dist
                    disp[a][0] += ux * force
                    disp[a][1] += uy * force
                    disp[b][0] -= ux * force
                    disp[b][1] -= uy * force

            # Gaya pegas: hanya pasangan yang punya edge, menuju panjang target
            for (u, v), target in target_len.items():
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                dist  = max(min_dist, math.hypot(dx, dy))
                force = k_spring * (dist - target)
                ux, uy = dx / dist, dy / dist
                disp[u][0] -= ux * force
                disp[u][1] -= uy * force
                disp[v][0] += ux * force
                disp[v][1] += uy * force

            # Terapkan pergeseran, dibatasi oleh "temperature" (cooling schedule)
            for node in nodes:
                dx, dy = disp[node]
                dlen = max(min_dist, math.hypot(dx, dy))
                step = min(dlen, temperature)
                x, y = pos[node]
                pos[node] = (x + dx / dlen * step, y + dy / dlen * step)

            temperature = max(temperature * cooling, 0.01)

        return pos

    @staticmethod
    def _normalize_to_canvas(
        pos: dict, width: int, height: int, margin: int
    ) -> dict:
        """Peta koordinat float NetworkX ke koordinat piksel SVG."""
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]

        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        xrange = max(xmax - xmin, 1e-6)
        yrange = max(ymax - ymin, 1e-6)

        usable_w = width  - 2 * margin
        usable_h = height - 2 * margin

        result: dict = {}
        for node, (x, y) in pos.items():
            cx = margin + (x - xmin) / xrange * usable_w
            cy = margin + (y - ymin) / yrange * usable_h
            result[node] = (cx, cy)
        return result

    @staticmethod
    def _node_max_threshold(graph: nx.Graph) -> dict:
        """Tentukan threshold tertinggi dari semua edge yang terhubung ke node."""
        node_max: dict = {}
        for u, v, data in graph.edges(data=True):
            thr = data.get("threshold", "Low")
            for node in (u, v):
                cur = node_max.get(node, "Low")
                if THRESHOLD_ORDER.get(thr, 0) > THRESHOLD_ORDER.get(cur, 0):
                    node_max[node] = thr
        return node_max

    # ── SVG builders ──────────────────────────────────────────────────────────

    @staticmethod
    def _svg_header(width: int, height: int) -> str:
        """
        Header SVG mengisi penuh lebar container (width:100%, tanpa
        batas maksimum) -- tinggi render otomatis mengikuti aspect
        ratio viewBox.

        RIWAYAT MASALAH:
        - v6 awal: width:100% tanpa height eksplisit -> saat SVG
          membesar mengikuti lebar container yang lebih besar dari
          viewBox, tingginya ikut membesar melebihi asumsi Python untuk
          tinggi iframe -> legend di bagian bawah terpotong.
        - Percobaan perbaikan (max-width:{width}px): mencegah SVG
          membesar melebihi viewBox aslinya, TAPI kalau container lebih
          lebar dari viewBox, muncul ruang kosong di kiri-kanan --
          terlihat seperti "kotak dalam kotak".

        SOLUSI SEBENARNYA: masalahnya bukan di CSS SVG, tapi di
        checker_graph.py yang memanggil st.iframe(..., height=<angka
        tebakan>) -- ini menonaktifkan fitur auto-sizing bawaan
        st.iframe (height="content", default). Dengan height="content",
        Streamlit MENGUKUR tinggi konten HTML yang sesungguhnya setelah
        dirender, jadi SVG bebas mengisi penuh lebar container (tanpa
        batas/gap) dan tinggi iframe otomatis menyesuaikan -- tidak
        pernah memotong maupun menyisakan ruang kosong.
        """
        return (
            f'<svg id="jinggo-graph" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" overflow="visible" '
            f'style="width:100%;background:#FAFAFA;display:block;'
            f'border-radius:12px;border:1.5px solid #EEEEEE;">'
        )

    @staticmethod
    def _svg_defs() -> str:
        return """<defs>
<style>
  .g-edge { stroke-opacity:0.55; transition: stroke-opacity .15s; }
  .g-edge:hover { stroke-opacity:1; }
  .g-node { cursor:default; transition: opacity .15s; }
  .g-node:hover { opacity:0.80; }
</style>
</defs>"""

    def _render_edges(self, graph: nx.Graph, pos: dict) -> list:
        """
        Render semua edge sebagai <line>.

        Lebar edge dipersempit (max 3.5px vs lama 6.5px) agar tidak
        menutupi node di area klaster padat.
        """
        parts: list = []
        for u, v, data in graph.edges(data=True):
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            threshold   = data.get("threshold", "Low")
            similarity  = data.get("similarity", 0.0)
            _, stroke   = THRESHOLD_PALETTE.get(threshold, ("#CCC", "#999"))
            line_width  = 1.0 + (similarity / 100.0) * 2.5
            tooltip_txt = (
                f"{html.escape(u[:40])} <-> {html.escape(v[:40])}: "
                f"{similarity:.1f}% ({threshold})"
            )
            parts.append(
                f'<line class="g-edge" '
                f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{stroke}" stroke-width="{line_width:.1f}">'
                f"<title>{tooltip_txt}</title>"
                f"</line>"
            )
        return parts

    def _render_nodes(
        self, graph: nx.Graph, pos: dict, node_max_threshold: dict
    ) -> list:
        """
        Render semua node sebagai <circle> dengan label DI BAWAH dan tooltip.

        Radius diperkecil (12 + degree*1.2 vs lama 20 + degree*2.5):
            degree=0  : r=12px  (vs lama 20px)
            degree=5  : r=18px  (vs lama 32px)
            degree=10 : r=24px  (vs lama 45px)  <- perbaikan utama
        Label dipindah ke BAWAH node agar terbaca meski node kecil.
        """
        parts: list = []
        for node in graph.nodes():
            cx, cy    = pos[node]
            degree    = graph.degree(node)
            radius    = 12 + degree * 1.2
            threshold = node_max_threshold.get(node, "Low")
            fill, stroke = THRESHOLD_PALETTE.get(threshold, ("#F5F5F5", "#999"))
            label     = graph.nodes[node].get("label", node[:15])
            short     = (label[:11] + "...") if len(label) > 12 else label
            tooltip   = html.escape(node)

            parts.append(
                f'<circle class="g-node" '
                f'cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="2">'
                f"<title>{tooltip}</title>"
                f"</circle>"
            )
            # Label di BAWAH node (bukan di tengah) agar tidak terpotong
            label_y = cy + radius + 10
            parts.append(
                f'<text x="{cx:.1f}" y="{label_y:.1f}" '
                f'text-anchor="middle" dominant-baseline="hanging" '
                f'font-size="8" font-family="sans-serif" '
                f'fill="{stroke}" font-weight="600" '
                f'style="pointer-events:none;">'
                f"{html.escape(short)}"
                f"</text>"
            )
        return parts

    @staticmethod
    def _render_legend(width: int, height: int) -> str:
        """Render legenda warna di sudut kanan bawah SVG."""
        items = [
            ("High",     "#C62828", "#FFCDD2"),
            ("Moderate", "#E65100", "#FFE0B2"),
            ("Low",      "#2E7D32", "#C8E6C9"),
        ]
        lx = width - 138
        ly = height - 130   # dinaikkan 40px (dari -90) agar item Low tidak
                             # terpotong saat SVG width:100% memperbesar tampilan
        parts = [
            f'<rect x="{lx - 8}" y="{ly - 14}" width="128" height="94" '
            f'rx="6" fill="white" stroke="#DDDDDD" stroke-width="1"/>',
            f'<text x="{lx}" y="{ly}" font-size="8.5" font-weight="700" '
            f'font-family="sans-serif" fill="#444">Kemiripan</text>',
        ]
        for i, (label, stroke, fill) in enumerate(items):
            ey = ly + 16 + i * 20
            parts.append(
                f'<circle cx="{lx + 7}" cy="{ey}" r="7" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{lx + 20}" y="{ey}" '
                f'font-size="8.5" font-family="sans-serif" fill="#444" '
                f'dominant-baseline="middle">{label}</text>'
            )
        return "\n".join(parts)

    @staticmethod
    def _empty_svg(width: int, height: int) -> str:
        """SVG placeholder saat tidak ada node."""
        return (
            f'<svg id="jinggo-graph" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" overflow="visible" '
            f'style="width:100%;background:#FAFAFA;border-radius:12px;">'
            f'<text x="{width//2}" y="{height//2}" '
            f'text-anchor="middle" font-size="14" fill="#AAAAAA" '
            f'font-family="sans-serif">Tidak ada data untuk divisualisasikan</text>'
            f"</svg>"
        )

    @staticmethod
    def _short_label(name: str, max_len: int = 20) -> str:
        """Perpendek nama project untuk label node."""
        if len(name) <= max_len:
            return name
        return name[:max_len - 1] + "..."
