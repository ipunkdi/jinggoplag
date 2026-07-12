"""
GraphService
============
Menghitung dan menghasilkan representasi graf kemiripan antar project
menggunakan algoritma *spring layout* dari NetworkX.

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

Menggunakan `seed=42` pada spring_layout agar tata letak graf
**reproducible** — input data yang sama selalu menghasilkan tampilan
yang persis sama (penting untuk konsistensi presentasi akademik).

Perbaikan v2 (pasca sidang):
- k = max(3.0, 1.8*log(n+1))  → untuk n=28: k≈6.1 (vs lama 1.4), node tidak berdesakan
- iterations = 150             → layout lebih konvergen
- radius = 12 + degree*1.2    → node lebih kecil (degree=10: 24px vs lama 45px)
- edge width max 3.5px         → vs lama 6.5px, klaster tidak gelap
- canvas dinamis               → tumbuh proporsional dengan n
- label di BAWAH node          → terbaca meski node kecil
"""

import html
import math

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
            Dict berisi jumlah node, edge, komponen terhubung, dan node terisolasi.
        """
        components     = list(nx.connected_components(graph))
        isolated_count = sum(1 for c in components if len(c) == 1)

        return {
            "node_count":      graph.number_of_nodes(),
            "edge_count":      graph.number_of_edges(),
            "component_count": len(components),
            "isolated_count":  isolated_count,
            "largest_cluster": max((len(c) for c in components), default=0),
        }

    def render_svg(
        self,
        graph: nx.Graph,
        width:  int = CANVAS_WIDTH,
        height: int = CANVAS_HEIGHT,
        margin: int = CANVAS_MARGIN,
    ) -> str:
        """
        Hasilkan string SVG interaktif dari NetworkX Graph.

        Canvas diperbesar secara dinamis sesuai jumlah node agar spring
        layout punya ruang yang cukup:
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
        Spring layout dengan k proporsional log(n) dan seed tetap.

        Formula k = max(3.0, 1.8*log(n+1)) menjamin jarak antar node
        selalu memadai untuk berbagai ukuran kelas:
            n=5  -> k=4.3  |  n=10 -> k=5.1  |  n=28 -> k=6.1  |  n=50 -> k=7.1
        Jauh lebih baik dari formula lama max(1.4, 3.2/sqrt(n)) yang untuk
        n=28 hanya menghasilkan k=1.4 sehingga node berdesakan.
        """
        n = max(graph.number_of_nodes(), 1)
        k = max(3.0, 1.8 * math.log(n + 1))
        return nx.spring_layout(graph, seed=42, k=k, iterations=150)

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
        lx = width - 130
        ly = height - 90
        parts = [
            f'<rect x="{lx - 8}" y="{ly - 14}" width="122" height="84" '
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
