"""
Halaman Checker Graph (tampilan alternatif Step 2).

Menampilkan graf jaringan kemiripan antar seluruh project — setiap node
adalah satu project mahasiswa dan setiap garis menghubungkan dua project
yang tingkat kemiripannya mencapai minimum yang ditentukan.

Tampilan ini melengkapi tabel di halaman Comparisons: alih-alih melihat
baris demi baris, dosen dapat langsung melihat "klaster" mahasiswa yang
saling menyalin dari satu pandangan, terutama saat ada lebih dari 20
project (skenario kelas penuh).

Akses: tombol "📊 Graf Kemiripan" di halaman Comparisons (Step 2).
Kembali: tombol "← Kembali ke Comparisons" atau navbar Plagiarism Checker.
"""

import re
import streamlit as st

from components.step_indicator import render_step_indicator
from services.graph_service    import GraphService, CANVAS_WIDTH, CANVAS_HEIGHT

ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_RESULT      = "checker_result"

_GRAPH_CSS = """
<style>
div[data-testid="stSlider"] label {
    font-size: 0.88rem !important;
    color: #555 !important;
}
div[data-testid="stMetric"] {
    background: #FAFAFA;
    border: 1px solid #EEEEEE;
    border-radius: 8px;
    padding: 0.5rem 0.8rem;
}
div[data-testid="stMetric"] label {
    font-size: 0.78rem !important;
}
</style>
"""


def render(navigate_to) -> None:
    """
    Render halaman Graf Kemiripan.

    Args:
        navigate_to: Callback navigasi dari app.py.
    """
    render_step_indicator(current_step=2)
    st.markdown(_GRAPH_CSS, unsafe_allow_html=True)

    comparison_results = st.session_state.get("comparison_results", [])

    if not comparison_results:
        st.info("Tidak ada data. Silakan unggah file dan jalankan analisis terlebih dahulu.")
        if st.button("← Kembali", key="btn_back_no_data"):
            navigate_to(ROUTE_COMPARISONS)
        return

    st.markdown(
        """
        <h2 style="font-size:1.4rem; font-weight:800; color:#1A1A1A;
                   margin-bottom:0.2rem;">Graf Kemiripan</h2>
        <p style="font-size:0.88rem; color:#777; margin-bottom:1.2rem;">
            Setiap <strong>simpul</strong> (lingkaran) mewakili satu project mahasiswa.
            Setiap <strong>garis</strong> menghubungkan dua project dengan similarity
            di atas ambang yang Anda pilih.<br>
            Ukuran simpul proporsional terhadap jumlah koneksi (degree).
            Warna merah = pernah terdeteksi <em>High</em> di setidaknya satu pasangan.
            <strong>Arahkan kursor</strong> ke simpul atau garis untuk melihat detail.
        </p>
        """,
        unsafe_allow_html=True,
    )

    svc = GraphService()

    # ── Kontrol filter ─────────────────────────────────────────────────────────
    col_slider, col_btn = st.columns([4, 1.3])

    with col_slider:
        min_sim = st.slider(
            label="Tampilkan koneksi dengan similarity minimal (%)",
            min_value=0,
            max_value=100,
            value=30,
            step=5,
            key="graph_min_sim_slider",
            help=(
                "Geser ke kanan untuk menyembunyikan koneksi dengan kemiripan rendah "
                "agar klaster yang signifikan lebih mudah terlihat. "
                "Nilai 30% = ambang batas minimum threshold Moderate."
            ),
        )

    with col_btn:
        st.markdown("<div style='padding-top:1.5rem;'></div>", unsafe_allow_html=True)
        if st.button(
            "← Kembali ke Comparisons",
            key="btn_back_to_comp_from_graph",
            use_container_width=True,
        ):
            navigate_to(ROUTE_COMPARISONS)

    # ── Bangun graf ────────────────────────────────────────────────────────────
    graph = svc.build_graph(comparison_results, min_similarity=float(min_sim))
    stats = svc.graph_stats(graph)

    # ── Statistik ringkas ──────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Project", stats["node_count"])
    with c2:
        st.metric("Koneksi Terdeteksi", stats["edge_count"])
    with c3:
        st.metric("Klaster Terpisah", stats["component_count"])
    with c4:
        st.metric("Terbesar Klaster", f"{stats['largest_cluster']} project")

    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

    # ── Peringatan khusus jika ada klaster besar ──────────────────────────────
    if stats["largest_cluster"] >= 4:
        st.warning(
            f"⚠️ Ditemukan klaster {stats['largest_cluster']} project yang saling terhubung "
            f"dengan similarity ≥ {min_sim}%. Perlu perhatian lebih lanjut."
        )
    elif stats["edge_count"] == 0:
        st.info(
            f"Tidak ada koneksi dengan similarity ≥ {min_sim}%. "
            f"Coba geser slider ke nilai lebih rendah."
        )

    # ── Render SVG graf dengan Pan & Zoom interaktif ───────────────────────────
    svg_html  = svc.render_svg(graph)

    # Baca dimensi viewBox AKTUAL dari SVG yang dihasilkan (canvas dinamis)
    # agar konversi koordinat mouse → SVG di JavaScript tetap akurat.
    _vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg_html)
    vw  = int(_vb.group(1)) if _vb else CANVAS_WIDTH
    vh  = int(_vb.group(2)) if _vb else CANVAS_HEIGHT

    full_html = _build_interactive_html(svg_html, vw, vh)
    # Tinggi iframe = vh + 120px buffer untuk mengakomodasi skala SVG
    # (SVG width:100% membesar di layar lebar, mendorong konten ke bawah)
    st.iframe(full_html, height=max(660, vh + 120))

    # ── Legenda node terisolasi ────────────────────────────────────────────────
    if stats["isolated_count"] > 0:
        st.markdown(
            f"<p style='font-size:0.82rem; color:#AAAAAA; margin-top:0.5rem;'>"
            f"ℹ️ {stats['isolated_count']} project tidak memiliki koneksi di atas "
            f"{min_sim}% (tetap ditampilkan sebagai simpul kecil tanpa garis).</p>",
            unsafe_allow_html=True,
        )

    # ── Tabel pasangan dengan similarity tertinggi ────────────────────────────
    _render_top_pairs_table(comparison_results, min_sim, navigate_to)


def _render_top_pairs_table(
    comparison_results: list,
    min_sim: float,
    navigate_to,
) -> None:
    """
    Render tabel ringkas: top-10 pasangan dengan similarity tertinggi
    yang sesuai dengan filter slider aktif.
    """
    filtered = [
        r for r in comparison_results if r.similarity >= min_sim
    ]

    if not filtered:
        return

    st.markdown(
        f"""
        <h3 style="font-size:1.1rem; font-weight:700; color:#1A1A1A;
                   margin-top:1.5rem; margin-bottom:0.5rem;">
            Top Pasangan (similarity ≥ {min_sim:.0f}%)
        </h3>
        """,
        unsafe_allow_html=True,
    )

    top10  = filtered[:10]
    header = st.columns([0.5, 3.5, 3.5, 1.5, 1])

    labels = ["#", "Project A", "Project B", "Similarity", "Aksi"]
    header_style = "font-weight:700; font-size:0.88rem; color:#1A1A1A;"
    for col, label in zip(header, labels):
        col.markdown(f"<div style='{header_style}'>{label}</div>",
                     unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin:4px 0 0 0; border:none; border-top:2px solid #1A1A1A;'>",
        unsafe_allow_html=True,
    )

    for idx, comp in enumerate(top10, start=1):
        c_idx, c_a, c_b, c_sim, c_act = st.columns([0.5, 3.5, 3.5, 1.5, 1])

        colors = {
            "High":     ("#FFEBEE", "#D32F2F"),
            "Moderate": ("#FFF3E0", "#E87722"),
            "Low":      ("#E8F5E9", "#2E7D32"),
        }
        bg, fg = colors.get(comp.threshold, ("#F5F5F5", "#555"))

        with c_idx:
            st.markdown(
                f"<div style='padding-top:0.6rem;color:#555;'>{idx}</div>",
                unsafe_allow_html=True,
            )
        with c_a:
            st.markdown(
                f"<div style='padding-top:0.55rem;font-size:0.85rem;color:#333;"
                f"word-break:break-word;'>{comp.project_a}</div>",
                unsafe_allow_html=True,
            )
        with c_b:
            st.markdown(
                f"<div style='padding-top:0.55rem;font-size:0.85rem;color:#333;"
                f"word-break:break-word;'>{comp.project_b}</div>",
                unsafe_allow_html=True,
            )
        with c_sim:
            st.markdown(
                f"<div style='padding-top:0.45rem;'>"
                f"<span style='background:{bg};color:{fg};font-weight:700;"
                f"font-size:0.85rem;padding:2px 8px;border-radius:16px;"
                f"white-space:nowrap;'>{comp.similarity:.1f}%</span></div>",
                unsafe_allow_html=True,
            )
        with c_act:
            if st.button("👁", key=f"graph_view_{idx}", help="Lihat perbandingan detail"):
                st.session_state["selected_comparison"] = comp
                st.session_state["selected_file_pair"]  = None
                navigate_to(ROUTE_RESULT)

        st.markdown(
            "<hr style='margin:0;border:none;border-top:1px solid #EEEEEE;'>",
            unsafe_allow_html=True,
        )

    if len(filtered) > 10:
        st.markdown(
            f"<p style='font-size:0.82rem;color:#AAAAAA;margin-top:0.3rem;'>"
            f"Menampilkan 10 dari {len(filtered)} pasangan. "
            f"Lihat tabel lengkap di halaman Comparisons.</p>",
            unsafe_allow_html=True,
        )


def _build_interactive_html(svg_html: str, vw: int = CANVAS_WIDTH, vh: int = CANVAS_HEIGHT) -> str:
    """
    Bungkus SVG dalam dokumen HTML penuh dengan JavaScript pan dan zoom.

    Args:
        svg_html: Output dari GraphService.render_svg().
        vw:       Lebar viewBox SVG aktual (dibaca dari tag <svg viewBox>).
        vh:       Tinggi viewBox SVG aktual.

    Fitur:
    - Scroll mouse -> zoom in/out (terpusat pada posisi kursor)
    - Drag (klik tahan + geser) -> pan ke segala arah
    - Tombol Reset -> kembali ke tampilan awal
    - Legend tetap FIXED di sudut kanan bawah (tidak ikut pan/zoom)

    vw/vh harus sesuai viewBox SVG aktual agar konversi koordinat
    mouse -> SVG akurat, terutama untuk canvas dinamis (n besar).
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#FAFAFA; overflow:hidden; font-family:sans-serif; }}
  #wrapper {{ position:relative; width:100%; }}
  #controls {{
    position:absolute; top:10px; left:10px; z-index:20;
    display:flex; align-items:center; gap:8px;
  }}
  #reset-btn {{
    background:#FFFFFF; border:1.5px solid #CCCCCC;
    border-radius:6px; padding:4px 12px;
    font-size:11px; color:#555; cursor:pointer;
    transition:border-color .15s, color .15s;
    user-select:none;
  }}
  #reset-btn:hover {{ border-color:#E87722; color:#E87722; }}
  #hint {{ font-size:10.5px; color:#AAAAAA; user-select:none; }}
</style>
</head>
<body>
<div id="wrapper">
  <div id="controls">
    <button id="reset-btn">&#8635; Reset</button>
    <span id="hint">Scroll: zoom &bull; Drag: geser</span>
  </div>
  {svg_html}
</div>
<script>
(function () {{
  var VW = {vw};
  var VH = {vh};
  var svg = document.getElementById('jinggo-graph');
  var grp = document.getElementById('graph-group');
  if (!svg || !grp) return;

  var s = 1, tx = 0, ty = 0;
  var dragging = false, lx = 0, ly = 0;

  function applyTransform() {{
    grp.setAttribute('transform',
      'translate(' + tx + ',' + ty + ') scale(' + s + ')');
  }}

  function toSVG(cx, cy) {{
    var r   = svg.getBoundingClientRect();
    return {{
      x: (cx - r.left) * VW / r.width,
      y: (cy - r.top)  * VH / r.height,
    }};
  }}

  svg.addEventListener('wheel', function (e) {{
    e.preventDefault();
    var p  = toSVG(e.clientX, e.clientY);
    var f  = e.deltaY < 0 ? 1.15 : (1 / 1.15);
    var ns = Math.min(Math.max(0.1, s * f), 10);
    tx = p.x - (p.x - tx) * (ns / s);
    ty = p.y - (p.y - ty) * (ns / s);
    s  = ns;
    applyTransform();
  }}, {{ passive: false }});

  svg.addEventListener('mousedown', function (e) {{
    if (e.button !== 0) return;
    dragging = true;
    var p = toSVG(e.clientX, e.clientY);
    lx = p.x; ly = p.y;
    svg.style.cursor = 'grabbing';
    e.preventDefault();
  }});

  document.addEventListener('mousemove', function (e) {{
    if (!dragging) return;
    var p = toSVG(e.clientX, e.clientY);
    tx += p.x - lx; ty += p.y - ly;
    lx = p.x; ly = p.y;
    applyTransform();
  }});

  document.addEventListener('mouseup', function () {{
    if (dragging) {{ dragging = false; svg.style.cursor = 'grab'; }}
  }});

  var rb = document.getElementById('reset-btn');
  if (rb) {{ rb.addEventListener('click', function () {{
    s = 1; tx = 0; ty = 0; applyTransform();
  }}); }}

  svg.style.cursor = 'grab';
}})();
</script>
</body>
</html>"""
