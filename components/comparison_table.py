"""
Comparison Table Component
===========================
Komponen tabel yang dapat digunakan ulang (reusable) oleh:
- checker_comparisons.py  → menampilkan tabel project-level
- checker_result.py       → menampilkan tabel file-level

Komponen ini mengabstraksi logika rendering tabel agar tidak
ada duplikasi kode antar halaman.

Fungsi publik:
    render_comparison_table(rows, columns, on_view_click, key_prefix)

Setiap baris mendukung:
- Badge threshold berwarna pada kolom similarity
- Ikon mata (👁) yang mentrigger callback navigasi
- Folder/file icon otomatis sesuai tipe data
"""

import streamlit as st
from dataclasses import dataclass
from typing import Callable, Any


# ---------------------------------------------------------------------------
# Data class untuk satu baris tabel
# ---------------------------------------------------------------------------

@dataclass
class TableRow:
    """
    Merepresentasikan satu baris dalam tabel perbandingan.

    Attributes:
        index:      Nomor urut (1-indexed), ditampilkan di kolom pertama
        label_a:    Label kolom kiri (nama project atau nama file)
        label_b:    Label kolom kanan (nama project atau nama file)
        similarity: Persentase kemiripan (0.0 – 100.0)
        threshold:  Kategori ("Low" | "Moderate" | "High")
        payload:    Data asli (ComparisonResult atau FilePairResult) yang
                    akan diteruskan ke callback saat ikon mata diklik
        icon_type:  "folder" atau "file" — menentukan ikon yang ditampilkan
    """
    index:      int
    label_a:    str
    label_b:    str
    similarity: float
    threshold:  str
    payload:    Any
    icon_type:  str = "folder"   # "folder" | "file"


# ---------------------------------------------------------------------------
# Threshold badge (shared utility)
# ---------------------------------------------------------------------------

def threshold_badge(similarity: float, threshold: str) -> str:
    """
    Menghasilkan HTML badge berwarna sesuai threshold.

    High     → background merah muda, teks merah
    Moderate → background oranye muda, teks oranye
    Low      → background hijau muda, teks hijau

    Args:
        similarity: Persentase 0.0 – 100.0
        threshold:  "Low" | "Moderate" | "High"

    Returns:
        String HTML badge siap-render
    """
    palette = {
        "High":     ("#FFEBEE", "#D32F2F"),
        "Moderate": ("#FFF3E0", "#E87722"),
        "Low":      ("#E8F5E9", "#2E7D32"),
    }
    bg, fg = palette.get(threshold, ("#F5F5F5", "#555555"))

    return (
        f"<span style='"
        f"background:{bg}; color:{fg}; font-weight:700; font-size:0.88rem; "
        f"padding:3px 10px; border-radius:20px; white-space:nowrap;"
        f"'>"
        f"{similarity:.1f}% "
        f"<span style='font-weight:400; font-size:0.78rem;'>({threshold})</span>"
        f"</span>"
    )


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_comparison_table(
    rows:            list[TableRow],
    col_a_header:    str,
    col_b_header:    str,
    on_view_click:   Callable[[Any], None],
    key_prefix:      str = "table",
    empty_message:   str = "Tidak ada data untuk ditampilkan.",
) -> None:
    """
    Merender tabel perbandingan generik.

    Args:
        rows:           List TableRow yang akan ditampilkan
        col_a_header:   Judul kolom kiri (misal: "Marimar_Project_Root")
        col_b_header:   Judul kolom kanan (misal: "Pulgoso_Project_Root")
        on_view_click:  Callback dipanggil saat ikon mata diklik,
                        menerima row.payload sebagai argumen
        key_prefix:     Prefix untuk key widget Streamlit (hindari konflik)
        empty_message:  Pesan yang ditampilkan saat rows kosong
    """
    if not rows:
        st.info(empty_message)
        return

    # --- Header Tabel ---
    _render_header(col_a_header, col_b_header)

    # --- Baris Data ---
    for row in rows:
        _render_row(row, on_view_click, key_prefix)
        st.markdown(
            "<hr style='margin:0; border:none; border-top:1px solid #EEEEEE;'>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Internal: Header
# ---------------------------------------------------------------------------

def _render_header(col_a_header: str, col_b_header: str) -> None:
    """Merender baris header dengan garis pemisah tebal di bawahnya."""
    col_idx, col_a, col_b, col_sim, col_view = st.columns([0.5, 3.5, 3.5, 2, 1])
    header_style = "font-weight:700; color:#1A1A1A; font-size:0.88rem; padding:4px 0;"

    with col_idx:
        st.markdown(f"<div style='{header_style}'>#</div>", unsafe_allow_html=True)

    with col_a:
        label = col_a_header[:22] + "…" if len(col_a_header) > 22 else col_a_header
        st.markdown(f"<div style='{header_style}'>{label}</div>", unsafe_allow_html=True)

    with col_b:
        label = col_b_header[:22] + "…" if len(col_b_header) > 22 else col_b_header
        st.markdown(f"<div style='{header_style}'>{label}</div>", unsafe_allow_html=True)

    with col_sim:
        st.markdown(
            f"<div style='{header_style}'>Similarity</div>",
            unsafe_allow_html=True,
        )

    with col_view:
        st.markdown(
            f"<div style='{header_style}'>View</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<hr style='margin:2px 0 0 0; border:none; border-top:2px solid #1A1A1A;'>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Internal: Satu Baris
# ---------------------------------------------------------------------------

def _render_row(
    row:           TableRow,
    on_view_click: Callable[[Any], None],
    key_prefix:    str,
) -> None:
    """Merender satu baris tabel."""
    col_idx, col_a, col_b, col_sim, col_view = st.columns([0.5, 3.5, 3.5, 2, 1])

    icon = "📁" if row.icon_type == "folder" else "📄"
    mono = "font-family:monospace;" if row.icon_type == "file" else ""

    with col_idx:
        st.markdown(
            f"<div style='padding-top:0.6rem; color:#666;'>{row.index}</div>",
            unsafe_allow_html=True,
        )

    with col_a:
        st.markdown(
            f"""
            <div style='padding-top:0.5rem; font-size:0.88rem; color:#333; {mono}'>
                {icon}&nbsp;{_safe(row.label_a)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            f"""
            <div style='padding-top:0.5rem; font-size:0.88rem; color:#333; {mono}'>
                {icon}&nbsp;{_safe(row.label_b)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_sim:
        badge = threshold_badge(row.similarity, row.threshold)
        st.markdown(
            f"<div style='padding-top:0.45rem;'>{badge}</div>",
            unsafe_allow_html=True,
        )

    with col_view:
        if st.button(
            "👁",
            key=f"{key_prefix}_view_{row.index}",
            help="Lihat detail",
        ):
            on_view_click(row.payload)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _safe(text: str) -> str:
    """Escape karakter HTML berbahaya dalam label."""
    import html
    return html.escape(str(text))