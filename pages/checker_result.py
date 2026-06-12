"""
Halaman Checker Result (Step 3)
================================
Menampilkan breakdown file-level dari dua proyek yang dipilih di Step 2.
Header: dua nama folder + "OVERVIEW" + "Total Similarity (Project Average): X%"
Tabel: kolom Index / File A / File B / Similarity / View
Klik ikon mata → navigasi ke Detail (Step 4)
"""

import streamlit as st
from pages.checker_comparisons import _threshold_badge


ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_DETAIL      = "checker_detail"


def render(navigate_to) -> None:
    """
    Merender halaman Result.

    Args:
        navigate_to: Callback navigasi dari app.py
    """
    from pages.checker_upload import _render_step_indicator
    _render_step_indicator(current_step=3)

    comparison = st.session_state.get("selected_comparison")

    if comparison is None:
        st.warning("Tidak ada proyek yang dipilih. Kembali ke halaman Comparisons.")
        if st.button("← Kembali", key="btn_back_comp"):
            navigate_to(ROUTE_COMPARISONS)
        return

    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Header dua folder proyek
    # ----------------------------------------------------------------
    _render_project_header(comparison.project_a, comparison.project_b)

    # ----------------------------------------------------------------
    # OVERVIEW
    # ----------------------------------------------------------------
    st.markdown(
        """
        <h3 style="
            text-align: center;
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: 2px;
            color: #1A1A1A;
            margin: 1.2rem 0 0.3rem 0;
        ">OVERVIEW</h3>
        """,
        unsafe_allow_html=True,
    )

    badge = _threshold_badge(comparison.similarity, comparison.threshold)
    st.markdown(
        f"""
        <p style="font-size:0.95rem; color:#333; margin-bottom:1.2rem;">
            <strong>Total Similarity (Project Average):</strong> {badge}
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------------------
    # Tabel File Pairs
    # ----------------------------------------------------------------
    file_pairs = comparison.file_pairs

    if not file_pairs:
        st.info("Tidak ada pasangan file yang ditemukan untuk proyek ini.")
        _back_button(navigate_to)
        return

    _render_table_header(comparison.project_a, comparison.project_b)

    for idx, file_pair in enumerate(file_pairs, start=1):
        _render_file_pair_row(
            index=idx,
            file_pair=file_pair,
            navigate_to=navigate_to,
        )
        st.markdown(
            "<hr style='margin:0; border:none; border-top:1px solid #EEEEEE;'>",
            unsafe_allow_html=True,
        )

    # Tombol kembali
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    _back_button(navigate_to)


# ---------------------------------------------------------------------------
# Header proyek
# ---------------------------------------------------------------------------

def _render_project_header(project_a: str, project_b: str) -> None:
    """Merender kartu header dua folder proyek berdampingan."""
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 1.5rem;
            border: 2px solid #CCCCCC;
            border-radius: 10px;
            padding: 0.8rem 1.5rem;
            background: #FAFAFA;
            margin-bottom: 0.5rem;
        ">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.4rem;">📁</span>
                <span style="font-weight:700; color:#1A1A1A; font-size:0.95rem;">
                    {project_a}
                </span>
            </div>
            <span style="color:#AAAAAA; font-size:1.2rem;">⟷</span>
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.4rem;">📁</span>
                <span style="font-weight:700; color:#1A1A1A; font-size:0.95rem;">
                    {project_b}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tabel Header
# ---------------------------------------------------------------------------

def _render_table_header(project_a: str, project_b: str) -> None:
    """Merender header tabel dengan nama kolom dinamis."""
    col_idx, col_fa, col_fb, col_sim, col_view = st.columns([0.5, 3, 3, 2, 1])

    header_style = "font-weight:700; color:#1A1A1A; font-size:0.88rem;"

    with col_idx:
        st.markdown(f"<div style='{header_style}'>#</div>", unsafe_allow_html=True)
    with col_fa:
        short_a = project_a[:20] + "…" if len(project_a) > 20 else project_a
        st.markdown(f"<div style='{header_style}'>{short_a}</div>", unsafe_allow_html=True)
    with col_fb:
        short_b = project_b[:20] + "…" if len(project_b) > 20 else project_b
        st.markdown(f"<div style='{header_style}'>{short_b}</div>", unsafe_allow_html=True)
    with col_sim:
        st.markdown(f"<div style='{header_style}'>Similarity</div>", unsafe_allow_html=True)
    with col_view:
        st.markdown(f"<div style='{header_style}'>View</div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin:4px 0 0 0; border:none; border-top:2px solid #1A1A1A;'>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Baris Tabel
# ---------------------------------------------------------------------------

def _render_file_pair_row(index: int, file_pair, navigate_to) -> None:
    """Merender satu baris pasangan file."""
    col_idx, col_fa, col_fb, col_sim, col_view = st.columns([0.5, 3, 3, 2, 1])

    with col_idx:
        st.markdown(
            f"<div style='padding-top:0.6rem; color:#555;'>{index}</div>",
            unsafe_allow_html=True,
        )
    with col_fa:
        st.markdown(
            f"""
            <div style='padding-top:0.55rem; font-size:0.88rem;
                        color:#333; font-family:monospace;'>
                {file_pair.file_a}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_fb:
        st.markdown(
            f"""
            <div style='padding-top:0.55rem; font-size:0.88rem;
                        color:#333; font-family:monospace;'>
                {file_pair.file_b}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_sim:
        badge = _threshold_badge(file_pair.similarity, file_pair.threshold)
        st.markdown(
            f"<div style='padding-top:0.45rem;'>{badge}</div>",
            unsafe_allow_html=True,
        )
    with col_view:
        if st.button("👁", key=f"view_fp_{index}", help="Lihat perbandingan kode"):
            st.session_state["selected_file_pair"] = file_pair
            navigate_to(ROUTE_DETAIL)


# ---------------------------------------------------------------------------
# Tombol kembali
# ---------------------------------------------------------------------------

def _back_button(navigate_to) -> None:
    if st.button("← Kembali ke Comparisons", key="btn_back_to_comp_from_result"):
        navigate_to(ROUTE_COMPARISONS)