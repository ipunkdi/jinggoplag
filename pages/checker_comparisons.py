"""
Halaman Checker Comparisons (Step 2)
=====================================
Menampilkan tabel "Top Comparisons" berisi semua pasangan proyek
diurutkan dari similarity tertinggi, dengan badge threshold berwarna.
Klik ikon mata → navigasi ke halaman Result (Step 3).
"""

import streamlit as st


ROUTE_RESULT = "checker_result"
ROUTE_UPLOAD = "checker_upload"


def render(navigate_to) -> None:
    """
    Merender halaman Comparisons.

    Args:
        navigate_to: Callback navigasi dari app.py
    """
    from pages.checker_upload import _render_step_indicator
    _render_step_indicator(current_step=2)

    comparison_results = st.session_state.get("comparison_results", [])

    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)

    # Header
    st.markdown(
        """
        <h2 style="
            font-size: 1.5rem;
            font-weight: 700;
            color: #1A1A1A;
            margin-bottom: 0.25rem;
        ">Top Comparisons:</h2>
        """,
        unsafe_allow_html=True,
    )

    if not comparison_results:
        st.info("Tidak ada data perbandingan. Silakan unggah file dan jalankan analisis.")
        if st.button("← Kembali ke Upload", key="btn_back_to_upload"):
            navigate_to(ROUTE_UPLOAD)
        return

    total = len(comparison_results)
    high_count = sum(1 for r in comparison_results if r.threshold == "High")
    mod_count  = sum(1 for r in comparison_results if r.threshold == "Moderate")

    # Ringkasan singkat
    st.markdown(
        f"""
        <p style="color:#777; font-size:0.88rem; margin-bottom:1.2rem;">
            {total} pasangan ditemukan &nbsp;·&nbsp;
            <span style="color:#D32F2F; font-weight:600;">{high_count} High</span> &nbsp;·&nbsp;
            <span style="color:#E87722; font-weight:600;">{mod_count} Moderate</span>
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------------------
    # Tabel Header
    # ----------------------------------------------------------------
    _render_table_header()

    # ----------------------------------------------------------------
    # Baris Tabel
    # ----------------------------------------------------------------
    for idx, comparison in enumerate(comparison_results, start=1):
        _render_comparison_row(
            index=idx,
            comparison=comparison,
            navigate_to=navigate_to,
        )
        st.markdown(
            "<hr style='margin:0; border:none; border-top:1px solid #EEEEEE;'>",
            unsafe_allow_html=True,
        )

    # Tombol "Analisis Baru"
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    if st.button("⟳  Analisis Baru", key="btn_new_analysis_comp"):
        navigate_to(ROUTE_UPLOAD)


# ---------------------------------------------------------------------------
# Tabel Header
# ---------------------------------------------------------------------------

def _render_table_header() -> None:
    """Merender baris header tabel."""
    col_idx, col_submissions, col_sim, col_view = st.columns([0.5, 5, 2, 1])

    header_style = "font-weight:700; color:#1A1A1A; font-size:0.9rem;"

    with col_idx:
        st.markdown(f"<div style='{header_style}'>#</div>", unsafe_allow_html=True)
    with col_submissions:
        st.markdown(
            f"<div style='{header_style}'>Submissions in Comparison</div>",
            unsafe_allow_html=True,
        )
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
        "<hr style='margin:4px 0 0 0; border:none; border-top:2px solid #1A1A1A;'>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Baris Tabel
# ---------------------------------------------------------------------------

def _render_comparison_row(index: int, comparison, navigate_to) -> None:
    """
    Merender satu baris data perbandingan proyek.

    Args:
        index:      Nomor urut (1-indexed)
        comparison: ComparisonResult object
        navigate_to: Callback navigasi
    """
    col_idx, col_submissions, col_sim, col_view = st.columns([0.5, 5, 2, 1])

    with col_idx:
        st.markdown(
            f"<div style='padding-top:0.6rem; color:#555;'>{index}</div>",
            unsafe_allow_html=True,
        )

    with col_submissions:
        # Dua folder berdampingan
        sub_l, sub_sep, sub_r = st.columns([2, 0.3, 2])
        with sub_l:
            st.markdown(
                f"""
                <div style='padding-top:0.5rem;'>
                    <span style='font-size:1.1rem;'>📁</span>
                    <span style='font-size:0.88rem; color:#333; margin-left:4px;
                                 word-break:break-word;'>
                        {comparison.project_a}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with sub_sep:
            st.markdown(
                "<div style='padding-top:0.6rem; color:#AAAAAA; text-align:center;'>vs</div>",
                unsafe_allow_html=True,
            )
        with sub_r:
            st.markdown(
                f"""
                <div style='padding-top:0.5rem;'>
                    <span style='font-size:1.1rem;'>📁</span>
                    <span style='font-size:0.88rem; color:#333; margin-left:4px;
                                 word-break:break-word;'>
                        {comparison.project_b}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_sim:
        badge_html = _threshold_badge(comparison.similarity, comparison.threshold)
        st.markdown(
            f"<div style='padding-top:0.45rem;'>{badge_html}</div>",
            unsafe_allow_html=True,
        )

    with col_view:
        # Tombol ikon mata
        if st.button("👁", key=f"view_comp_{index}", help="Lihat detail perbandingan"):
            st.session_state["selected_comparison"] = comparison
            st.session_state["selected_file_pair"]  = None  # Reset pilihan file
            navigate_to(ROUTE_RESULT)


# ---------------------------------------------------------------------------
# Badge helper
# ---------------------------------------------------------------------------

def _threshold_badge(similarity: float, threshold: str) -> str:
    """
    Menghasilkan HTML badge berwarna sesuai threshold.

    High     → merah
    Moderate → oranye
    Low      → hijau
    """
    colors = {
        "High":     ("#FFEBEE", "#D32F2F"),  # background, text
        "Moderate": ("#FFF3E0", "#E87722"),
        "Low":      ("#E8F5E9", "#2E7D32"),
    }
    bg, fg = colors.get(threshold, ("#F5F5F5", "#555555"))

    return (
        f"<span style='"
        f"background:{bg}; color:{fg}; font-weight:700; font-size:0.88rem;"
        f"padding:3px 10px; border-radius:20px; white-space:nowrap;"
        f"'>"
        f"{similarity:.1f}% "
        f"<span style='font-weight:400; font-size:0.78rem;'>({threshold})</span>"
        f"</span>"
    )