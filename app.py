"""
app.py — Entry Point Jinggo Plag
=================================
Mengelola:
1. Inisialisasi session_state sebagai "volatile database"
2. Protected sequential routing (wizard flow)
3. Injeksi custom CSS
4. Dispatch ke halaman yang tepat

Workflow yang dilindungi:
    Home → Upload → Comparisons → Result → Detail
                     (Step 1)     (Step 2)  (Step 3)  (Step 4)

Setiap halaman setelah Upload memverifikasi bahwa data upstream
sudah tersedia di session_state sebelum merender konten.
"""

import streamlit as st
from pathlib import Path


# ---------------------------------------------------------------------------
# Konfigurasi halaman — HARUS dipanggil pertama kali sebelum import lain
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Jinggo Plag",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Import halaman (setelah set_page_config)
# ---------------------------------------------------------------------------
from pages.home               import render as render_home
from pages.checker_upload     import render as render_upload
from pages.checker_comparisons import render as render_comparisons
from pages.checker_result     import render as render_result
from pages.checker_detail     import render as render_detail
from pages.about              import render as render_about
from components.navbar        import render_navbar


# ---------------------------------------------------------------------------
# Konstanta Route
# ---------------------------------------------------------------------------
ROUTE_HOME        = "home"
ROUTE_UPLOAD      = "checker_upload"
ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_RESULT      = "checker_result"
ROUTE_DETAIL      = "checker_detail"
ROUTE_ABOUT       = "about"


# ---------------------------------------------------------------------------
# Inisialisasi Session State
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    """
    Menginisialisasi semua key session_state dengan nilai default.
    Dipanggil sekali saat aplikasi pertama kali dimuat.

    session_state berfungsi sebagai "volatile in-memory database":
    - Tidak ada data yang ditulis ke disk
    - Semua data hilang saat session Streamlit berakhir
    - Menjamin privasi source code mahasiswa
    """
    defaults = {
        # --- Routing ---
        "current_route": ROUTE_HOME,

        # --- Data pipeline (diisi oleh checker_upload setelah analisis selesai) ---
        # Dict: { project_name: { filename: raw_source_code } }
        "projects_raw": None,

        # Dict: { project_name: { filename: PreprocessedFile } }
        "projects_preprocessed": None,

        # Dict: { project_name: { filename: FingerprintResult } }
        "fingerprint_data": None,

        # List[ComparisonResult] — diurutkan dari similarity tertinggi
        "comparison_results": None,

        # --- State navigasi antar halaman ---
        # ComparisonResult yang dipilih di halaman Comparisons
        "selected_comparison": None,

        # FilePairResult yang dipilih di halaman Result
        "selected_file_pair": None,

        # --- UI state ---
        "analysis_running": False,
        "upload_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Navigasi helper (digunakan oleh semua halaman)
# ---------------------------------------------------------------------------

def navigate_to(route: str) -> None:
    """
    Berpindah ke route tertentu dan memicu rerun Streamlit.
    Diimpor oleh halaman-halaman yang membutuhkan navigasi.
    """
    st.session_state["current_route"] = route
    st.rerun()


def reset_analysis() -> None:
    """
    Mereset seluruh state analisis ke kondisi awal.
    Dipanggil saat pengguna ingin mengunggah file baru.
    """
    keys_to_reset = [
        "projects_raw",
        "projects_preprocessed",
        "fingerprint_data",
        "comparison_results",
        "selected_comparison",
        "selected_file_pair",
        "analysis_running",
        "upload_error",
    ]
    for key in keys_to_reset:
        st.session_state[key] = None
    st.session_state["analysis_running"] = False
    st.session_state["upload_error"]     = None


# ---------------------------------------------------------------------------
# CSS Injection
# ---------------------------------------------------------------------------

def _inject_css() -> None:
    """
    Menyuntikkan custom CSS global.
    Memuat dari file styles/main.css jika tersedia,
    atau menggunakan inline CSS sebagai fallback.
    """
    css_path = Path(__file__).parent / "styles" / "main.css"

    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
    else:
        css_content = _get_fallback_css()

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def _get_fallback_css() -> str:
    """CSS minimal sebagai fallback jika file main.css belum ada."""
    return """
        /* Sembunyikan sidebar bawaan Streamlit */
        [data-testid="stSidebar"] { display: none; }
        [data-testid="collapsedControl"] { display: none; }

        /* Reset padding halaman */
        .main .block-container {
            padding-top: 0rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }

        /* Sembunyikan menu hamburger dan footer Streamlit */
        #MainMenu { visibility: hidden; }
        footer    { visibility: hidden; }
        header    { visibility: hidden; }
    """


# ---------------------------------------------------------------------------
# Protected Route Guard
# ---------------------------------------------------------------------------

def _guard_route(route: str) -> str:
    """
    Memverifikasi apakah pengguna boleh mengakses route tertentu.
    Jika data upstream belum tersedia, redirect ke halaman yang sesuai.

    Returns:
        Route yang valid untuk dirender (mungkin berbeda dari input
        jika terjadi redirect)
    """
    if route == ROUTE_COMPARISONS:
        if st.session_state.get("comparison_results") is None:
            st.warning("⚠️ Analisis belum dijalankan. Silakan unggah file terlebih dahulu.")
            return ROUTE_UPLOAD

    elif route == ROUTE_RESULT:
        if st.session_state.get("comparison_results") is None:
            return ROUTE_UPLOAD
        if st.session_state.get("selected_comparison") is None:
            return ROUTE_COMPARISONS

    elif route == ROUTE_DETAIL:
        if st.session_state.get("comparison_results") is None:
            return ROUTE_UPLOAD
        if st.session_state.get("selected_comparison") is None:
            return ROUTE_COMPARISONS
        if st.session_state.get("selected_file_pair") is None:
            return ROUTE_RESULT

    return route


# ---------------------------------------------------------------------------
# Router Utama
# ---------------------------------------------------------------------------

def _render_current_page() -> None:
    """
    Menentukan dan merender halaman berdasarkan current_route di session_state.
    Semua halaman menerima fungsi navigate_to dan reset_analysis sebagai callback.
    """
    raw_route = st.session_state.get("current_route", ROUTE_HOME)
    route = _guard_route(raw_route)

    # Update route jika terjadi redirect oleh guard
    if route != raw_route:
        st.session_state["current_route"] = route

    # Dispatch ke halaman yang sesuai
    if route == ROUTE_HOME:
        render_home(navigate_to=navigate_to)

    elif route == ROUTE_UPLOAD:
        render_upload(navigate_to=navigate_to, reset_analysis=reset_analysis)

    elif route == ROUTE_COMPARISONS:
        render_comparisons(navigate_to=navigate_to)

    elif route == ROUTE_RESULT:
        render_result(navigate_to=navigate_to)

    elif route == ROUTE_DETAIL:
        render_detail(navigate_to=navigate_to)

    elif route == ROUTE_ABOUT:
        render_about(navigate_to=navigate_to)

    else:
        # Fallback ke home jika route tidak dikenal
        st.session_state["current_route"] = ROUTE_HOME
        render_home(navigate_to=navigate_to)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session_state()
    _inject_css()
    render_navbar(navigate_to=navigate_to)
    _render_current_page()


if __name__ == "__main__":
    main()