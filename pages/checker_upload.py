"""
Halaman Checker Upload (Step 1) — Fixed
========================================
Perbaikan:
- Full-viewport, non-scrollable layout
- Tombol START ANALYSIS selalu visible (tidak hilang)
- Progress bar muncul di bawah tombol dengan benar
"""
import streamlit as st
from pathlib import PurePosixPath

from services.extractor    import ZipExtractorService
from services.preprocessor import PreprocessorService
from services.fingerprint  import FingerprintService
from services.similarity   import SimilarityService

ROUTE_COMPARISONS = "checker_comparisons"


def render(navigate_to, reset_analysis) -> None:
    _render_step_indicator(current_step=1)

    # CSS: viewport fit, no scroll
    st.markdown("""
    <style>
    /* Full viewport upload page - no scroll */
    section.main > div.block-container {
        overflow: hidden !important;
        max-height: calc(100vh - 100px) !important;
    }
    /* START ANALYSIS button */
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
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding-top:1.5rem;'></div>", unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        _render_upload_card(navigate_to, reset_analysis)


def _render_upload_card(navigate_to, reset_analysis) -> None:
    # Judul kartu
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # Error display
    if st.session_state.get("upload_error"):
        st.error(st.session_state["upload_error"])
        st.session_state["upload_error"] = None

    # File uploader
    uploaded_file = st.file_uploader(
        label="Upload files (*.zip)",
        type=["zip"],
        key="zip_uploader",
        help="Arsip .zip berisi subfolder project mahasiswa.",
    )

    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

    # Tampilkan info file yang dipilih
    if uploaded_file is not None:
        size_kb = len(uploaded_file.getvalue()) / 1024
        st.markdown(
            f"<p style='text-align:center; color:#555; font-size:0.85rem; margin-bottom:0.5rem;'>"
            f"📦 <strong>{uploaded_file.name}</strong> ({size_kb:.1f} KB)</p>",
            unsafe_allow_html=True,
        )

    # --- Tombol START ANALYSIS — selalu render, disabled jika belum ada file ---
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        start_clicked = st.button(
            "START ANALYSIS",
            key="btn_start_analysis",
            disabled=(uploaded_file is None),
            use_container_width=True,
        )

    # Progress placeholder — hanya muncul saat analisis berjalan
    progress_placeholder = st.empty()

    if start_clicked and uploaded_file is not None:
        reset_analysis()
        _run_analysis_pipeline(uploaded_file.getvalue(), navigate_to, progress_placeholder)


def _run_analysis_pipeline(zip_bytes: bytes, navigate_to, progress_placeholder) -> None:
    with progress_placeholder.container():
        progress_bar = st.progress(0, text="Memulai analisis...")

        try:
            progress_bar.progress(10, text="📦 Mengekstrak arsip .zip...")
            extractor = ZipExtractorService(zip_bytes)
            projects_raw = extractor.extract()
            total_projects = len(projects_raw)
            total_files    = sum(len(f) for f in projects_raw.values())
            st.session_state["projects_raw"] = projects_raw

            progress_bar.progress(25, text=f"✅ {total_projects} project, {total_files} file ditemukan")

            progress_bar.progress(30, text="🔧 Preprocessing source code...")
            preprocessor = PreprocessorService()
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
            fp_service = FingerprintService()
            fingerprint_data = {}
            for proj, files in projects_preprocessed.items():
                fingerprint_data[proj] = {}
                for fname, prep in files.items():
                    fingerprint_data[proj][fname] = fp_service.compute(
                        processed_text=prep.processed,
                        original_text=prep.original,
                        char_map=prep.char_map,
                    )
            st.session_state["fingerprint_data"] = fingerprint_data

            progress_bar.progress(75, text="✅ Fingerprint diekstrak")

            progress_bar.progress(80, text="📊 Menghitung Jaccard Similarity...")
            sim_service = SimilarityService()
            comparison_results = sim_service.compute_all(fingerprint_data)
            st.session_state["comparison_results"] = comparison_results
            total_pairs = len(comparison_results)

            progress_bar.progress(100, text=f"✅ Selesai — {total_pairs} pasangan ditemukan")
            st.success(f"🎉 Analisis selesai! **{total_pairs} pasangan** dari **{total_projects} project**.")

            import time; time.sleep(0.8)
            navigate_to(ROUTE_COMPARISONS)

        except ValueError as e:
            progress_bar.empty()
            st.session_state["upload_error"] = str(e)
            st.error(f"❌ {e}")
        except Exception as e:
            progress_bar.empty()
            msg = f"Kesalahan: {type(e).__name__}: {e}"
            st.session_state["upload_error"] = msg
            st.error(f"❌ {msg}")


def _render_step_indicator(current_step: int) -> None:
    steps = [(1,"Upload"),(2,"Comparisons"),(3,"Result"),(4,"Detail")]
    parts = []
    for n, label in steps:
        if n == current_step:
            s = f'<span style="color:#E87722;font-weight:700;">Step {n}: {label}</span>'
        elif n < current_step:
            s = f'<span style="color:#BBBBBB;text-decoration:line-through;">Step {n}: {label}</span>'
        else:
            s = f'<span style="color:#CCCCCC;">Step {n}: {label}</span>'
        parts.append(s)
    sep = ' <span style="color:#CCCCCC;margin:0 0.4rem;">›</span> '
    st.markdown(
        f'<div style="text-align:center;font-size:0.88rem;padding:0.4rem 0;">{sep.join(parts)}</div>',
        unsafe_allow_html=True,
    )
