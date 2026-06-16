"""
Halaman Checker Upload (Step 1).

Layout full-viewport, non-scrollable.
Tombol START ANALYSIS selalu visible (disabled saat belum ada file).
"""

import time
from pathlib import PurePosixPath

import streamlit as st

from components.step_indicator import render_step_indicator
from services.extractor        import ZipExtractorService
from services.fingerprint      import FingerprintService
from services.preprocessor     import PreprocessorService
from services.similarity       import SimilarityService

ROUTE_COMPARISONS = "checker_comparisons"

_UPLOAD_CSS = """
<style>
section.main > div.block-container {
    overflow: hidden !important;
    max-height: calc(100vh - 100px) !important;
}
div[data-testid="stButton"] > button {
    background-color: #FFFFFF;
    color: #1A1A1A;
    border: 2px solid #1A1A1A;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.92rem;
    letter-spacing: 0.5px;
    padding: 0.5rem 1.5rem;
    transition: all 0.18s ease;
}
div[data-testid="stButton"] > button:hover {
    background-color: #E87722 !important;
    border-color: #E87722 !important;
    color: #FFFFFF !important;
}
div[data-testid="stButton"] > button:disabled {
    background-color: #F5F5F5 !important;
    border-color: #CCCCCC !important;
    color: #AAAAAA !important;
}
</style>
"""


def render(navigate_to, reset_analysis) -> None:
    """Render halaman Upload."""
    render_step_indicator(current_step=1)
    st.markdown(_UPLOAD_CSS, unsafe_allow_html=True)
    st.markdown("<div style='padding-top:1.5rem;'></div>", unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        _render_upload_card(navigate_to, reset_analysis)


def _render_upload_card(navigate_to, reset_analysis) -> None:
    """Render kartu upload dengan judul, file uploader, dan tombol START ANALYSIS."""
    st.markdown(
        """
        <div style="
            border: 2px solid #CCCCCC;
            border-radius: 12px 12px 0 0;
            padding: 1.2rem 2rem 1rem 2rem;
            background: #FAFAFA;
            text-align: center;
        ">
            <h3 style="margin:0; font-size:1.3rem; font-weight:700; color:#1A1A1A;">
                Compare Projects (.zip)
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("upload_error"):
        st.error(st.session_state["upload_error"])
        st.session_state["upload_error"] = None

    uploaded_file = st.file_uploader(
        label="Upload files (*.zip)",
        type=["zip"],
        key="zip_uploader",
        help="Arsip .zip berisi subfolder project mahasiswa.",
    )

    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

    if uploaded_file is not None:
        size_kb = len(uploaded_file.getvalue()) / 1024
        st.markdown(
            f"<p style='text-align:center;color:#555;font-size:0.85rem;"
            f"margin-bottom:0.5rem;'>"
            f"📦 <strong>{uploaded_file.name}</strong> ({size_kb:.1f} KB)</p>",
            unsafe_allow_html=True,
        )

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        start_clicked = st.button(
            "START ANALYSIS",
            key="btn_start_analysis",
            disabled=(uploaded_file is None),
            use_container_width=True,
        )

    progress_placeholder = st.empty()

    if start_clicked and uploaded_file is not None:
        reset_analysis()
        _run_analysis_pipeline(
            uploaded_file.getvalue(), navigate_to, progress_placeholder
        )


def _run_analysis_pipeline(zip_bytes: bytes, navigate_to, progress_placeholder) -> None:
    """
    Jalankan pipeline analisis lengkap.

    Tahap: Extraction → Preprocessing → Fingerprinting → Jaccard.
    Semua hasil disimpan ke st.session_state (volatile, tidak ditulis ke disk).
    """
    with progress_placeholder.container():
        progress_bar = st.progress(0, text="Memulai analisis...")

        try:
            _run_pipeline_steps(zip_bytes, navigate_to, progress_bar)
        except ValueError as exc:
            progress_bar.empty()
            st.session_state["upload_error"] = str(exc)
            st.error(f"❌ {exc}")
        except (OSError, MemoryError, RuntimeError) as exc:
            progress_bar.empty()
            msg = f"Kesalahan sistem: {type(exc).__name__}: {exc}"
            st.session_state["upload_error"] = msg
            st.error(f"❌ {msg}")


def _run_pipeline_steps(zip_bytes: bytes, navigate_to, progress_bar) -> None:
    """Eksekusi setiap tahap pipeline dan perbarui progress bar."""
    progress_bar.progress(10, text="📦 Mengekstrak arsip .zip...")
    extractor      = ZipExtractorService(zip_bytes)
    projects_raw   = extractor.extract()
    total_projects = len(projects_raw)
    total_files    = sum(len(f) for f in projects_raw.values())
    st.session_state["projects_raw"] = projects_raw
    progress_bar.progress(
        25, text=f"✅ {total_projects} project, {total_files} file ditemukan"
    )

    progress_bar.progress(30, text="🔧 Preprocessing source code...")
    preprocessor          = PreprocessorService()
    projects_preprocessed = {}

    for proj, files in projects_raw.items():
        projects_preprocessed[proj] = {}
        for fname, code in files.items():
            ext = PurePosixPath(fname).suffix.lower()
            try:
                projects_preprocessed[proj][fname] = preprocessor.preprocess(code, ext)
            except ValueError:
                pass

    st.session_state["projects_preprocessed"] = projects_preprocessed
    progress_bar.progress(50, text="✅ Preprocessing selesai")

    progress_bar.progress(55, text="🔑 Menghitung fingerprint (Rabin-Karp + Winnowing)...")
    fp_service       = FingerprintService()
    fingerprint_data = {}

    for proj, files in projects_preprocessed.items():
        fingerprint_data[proj] = {}
        for fname, prep in files.items():
            fingerprint_data[proj][fname] = fp_service.compute(
                processed_text=prep.processed,
                char_map=prep.char_map,
            )

    st.session_state["fingerprint_data"] = fingerprint_data
    progress_bar.progress(75, text="✅ Fingerprint diekstrak")

    progress_bar.progress(80, text="📊 Menghitung Jaccard Similarity...")
    sim_service        = SimilarityService()
    comparison_results = sim_service.compute_all(fingerprint_data)
    st.session_state["comparison_results"] = comparison_results
    total_pairs = len(comparison_results)

    progress_bar.progress(
        100, text=f"✅ Selesai — {total_pairs} pasangan ditemukan"
    )
    st.success(
        f"🎉 Analisis selesai! **{total_pairs} pasangan** "
        f"dari **{total_projects} project**."
    )
    time.sleep(0.8)
    navigate_to(ROUTE_COMPARISONS)
