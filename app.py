"""
app.py — Entry Point Jinggo Plag.

Mengelola:
1. Konfigurasi halaman Streamlit
2. Inisialisasi session_state sebagai volatile database
3. Protected sequential routing (wizard flow)
4. Injeksi custom CSS
5. Dispatch ke halaman yang tepat

Workflow yang dilindungi:
    Home → Upload → Comparisons → Result → Detail
"""

import streamlit as st  # noqa: E402

st.set_page_config(
    page_title="Jinggo Plag",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from pathlib import Path  # noqa: E402

from components.navbar         import render_navbar       # noqa: E402
from pages.about               import render as render_about        # noqa: E402
from pages.checker_comparisons import render as render_comparisons  # noqa: E402
from pages.checker_detail      import render as render_detail       # noqa: E402
from pages.checker_result      import render as render_result       # noqa: E402
from pages.checker_upload      import render as render_upload       # noqa: E402
from pages.home                import render as render_home         # noqa: E402

ROUTE_HOME        = "home"
ROUTE_UPLOAD      = "checker_upload"
ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_RESULT      = "checker_result"
ROUTE_DETAIL      = "checker_detail"
ROUTE_ABOUT       = "about"


def _init_session_state() -> None:
    """
    Inisialisasi semua key session_state dengan nilai default.

    session_state berfungsi sebagai volatile in-memory database:
    data hilang saat session Streamlit berakhir — menjamin privasi source code.
    """
    defaults = {
        "current_route":        ROUTE_HOME,
        "projects_raw":         None,
        "projects_preprocessed": None,
        "fingerprint_data":     None,
        "comparison_results":   None,
        "selected_comparison":  None,
        "selected_file_pair":   None,
        "analysis_running":     False,
        "upload_error":         None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate_to(route: str) -> None:
    """
    Pindah ke route tertentu dan trigger rerun Streamlit.

    Args:
        route: Konstanta route tujuan.
    """
    st.session_state["current_route"] = route
    st.rerun()


def reset_analysis() -> None:
    """Reset seluruh state analisis ke kondisi awal."""
    keys_to_reset = [
        "projects_raw", "projects_preprocessed", "fingerprint_data",
        "comparison_results", "selected_comparison", "selected_file_pair",
    ]
    for key in keys_to_reset:
        st.session_state[key] = None
    st.session_state["analysis_running"] = False
    st.session_state["upload_error"]     = None


def _inject_css() -> None:
    """Suntikkan custom CSS global dari file styles/main.css."""
    css_path = Path(__file__).parent / "styles" / "main.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
    else:
        css_content = (
            "[data-testid='stSidebar'] { display: none !important; }"
            "[data-testid='collapsedControl'] { display: none !important; }"
            ".main .block-container { padding-top: 0rem; max-width: 1200px; }"
            "#MainMenu { visibility: hidden; }"
            "footer { visibility: hidden; }"
            "header { visibility: hidden; }"
        )
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def _guard_route(route: str) -> str:
    """
    Verifikasi apakah pengguna boleh mengakses route tertentu.

    Args:
        route: Route yang diminta.

    Returns:
        Route yang valid (mungkin berbeda jika terjadi redirect).
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


def _render_current_page() -> None:
    """Tentukan dan render halaman berdasarkan current_route di session_state."""
    raw_route = st.session_state.get("current_route", ROUTE_HOME)
    route     = _guard_route(raw_route)

    if route != raw_route:
        st.session_state["current_route"] = route

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
        st.session_state["current_route"] = ROUTE_HOME
        render_home(navigate_to=navigate_to)


def main() -> None:
    """Entry point utama aplikasi Jinggo Plag."""
    _init_session_state()
    _inject_css()
    render_navbar(navigate_to=navigate_to)
    _render_current_page()


if __name__ == "__main__":
    main()
