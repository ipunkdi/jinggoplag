"""
Halaman Checker Comparisons (Step 2).

Menampilkan tabel "Top Comparisons" berisi semua pasangan proyek
diurutkan dari similarity tertinggi, dengan badge threshold berwarna.
Klik ikon mata → navigasi ke halaman Result (Step 3).
Tombol "Export PDF" → unduh laporan ringkasan seluruh pasangan.
"""

from datetime import datetime

import streamlit as st

from components.step_indicator  import render_step_indicator
from services.report_generator  import ReportGeneratorService

ROUTE_RESULT = "checker_result"
ROUTE_UPLOAD = "checker_upload"


def render(navigate_to) -> None:
    """
    Render halaman Comparisons.

    Args:
        navigate_to: Callback navigasi dari app.py.
    """
    render_step_indicator(current_step=2)

    comparison_results = st.session_state.get("comparison_results", [])

    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)

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

    total      = len(comparison_results)
    high_count = sum(1 for r in comparison_results if r.threshold == "High")
    mod_count  = sum(1 for r in comparison_results if r.threshold == "Moderate")

    col_stats, col_export = st.columns([4, 1.3])

    with col_stats:
        st.markdown(
            f"""
            <p style="color:#777; font-size:0.88rem; margin-bottom:1.2rem;
                       padding-top: 0.4rem;">
                {total} pasangan ditemukan &nbsp;·&nbsp;
                <span style="color:#D32F2F; font-weight:600;">{high_count} High</span>
                &nbsp;·&nbsp;
                <span style="color:#E87722; font-weight:600;">{mod_count} Moderate</span>
            </p>
            """,
            unsafe_allow_html=True,
        )

    with col_export:
        _render_export_button(comparison_results)

    _render_table_header()

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

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    if st.button("⟳  Analisis Baru", key="btn_new_analysis_comp"):
        navigate_to(ROUTE_UPLOAD)


def _render_table_header() -> None:
    """Render baris header tabel."""
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


def _render_comparison_row(index: int, comparison, navigate_to) -> None:
    """Render satu baris data perbandingan proyek."""
    col_idx, col_submissions, col_sim, col_view = st.columns([0.5, 5, 2, 1])

    with col_idx:
        st.markdown(
            f"<div style='padding-top:0.6rem; color:#555;'>{index}</div>",
            unsafe_allow_html=True,
        )

    with col_submissions:
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
        if st.button("👁", key=f"view_comp_{index}", help="Lihat detail perbandingan"):
            st.session_state["selected_comparison"] = comparison
            st.session_state["selected_file_pair"]  = None
            navigate_to(ROUTE_RESULT)


def _threshold_badge(similarity: float, threshold: str) -> str:
    """Hasilkan HTML badge berwarna sesuai threshold."""
    colors = {
        "High":     ("#FFEBEE", "#D32F2F"),
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


def _render_export_button(comparison_results: list) -> None:
    """
    Render tombol unduh laporan PDF ringkasan seluruh pasangan.

    PDF dihasilkan langsung saat halaman dirender (generasi cepat,
    < 200ms untuk ratusan pasangan) dan disuguhkan sebagai SATU tombol
    unduh — sekali klik langsung memicu download browser, tanpa
    langkah "generate" terpisah sebelumnya.
    """
    st.markdown("<div style='padding-top: 0.4rem;'></div>", unsafe_allow_html=True)

    report_service = ReportGeneratorService()
    pdf_bytes      = report_service.generate_summary_report(comparison_results)
    timestamp      = datetime.now().strftime("%Y%m%d_%H%M")

    st.download_button(
        label="📄 Export PDF",
        data=pdf_bytes,
        file_name=f"jinggoplag_ringkasan_{timestamp}.pdf",
        mime="application/pdf",
        key="btn_export_summary",
        use_container_width=True,
    )
