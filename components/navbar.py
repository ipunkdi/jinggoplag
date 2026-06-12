"""
Navbar Component — Fixed
========================
Perbaikan:
1. Tombol tidak muncul ganda (hapus invisible button overlay)
2. Sticky navbar via CSS
3. Layout bersih dengan st.columns
"""

import streamlit as st

ROUTE_HOME        = "home"
ROUTE_UPLOAD      = "checker_upload"
ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_ABOUT       = "about"

def render_navbar(navigate_to) -> None:
    current_route = st.session_state.get("current_route", ROUTE_HOME)

    home_active    = current_route == ROUTE_HOME
    checker_active = current_route in (ROUTE_UPLOAD, ROUTE_COMPARISONS, "checker_result", "checker_detail")
    about_active   = current_route == ROUTE_ABOUT

    # Inject sticky navbar CSS sekali saja
    st.markdown("""
    <style>
    /* Sticky navbar container */
    div[data-testid="stVerticalBlock"] > div:first-child {
        position: sticky;
        top: 0;
        z-index: 999;
        background: white;
    }
    /* Sembunyikan border default tombol Streamlit di navbar */
    .nav-btn > div[data-testid="stButton"] > button {
        background: transparent !important;
        border: none !important;
        padding: 0.2rem 0.5rem !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        color: #333333 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        letter-spacing: 0 !important;
    }
    .nav-btn > div[data-testid="stButton"] > button:hover {
        background: transparent !important;
        color: #E87722 !important;
        border: none !important;
    }
    .nav-btn-active > div[data-testid="stButton"] > button {
        background: transparent !important;
        border: none !important;
        padding: 0.2rem 0.5rem !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: #E87722 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    .nav-btn-active > div[data-testid="stButton"] > button:hover {
        background: transparent !important;
        color: #E87722 !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_logo, col_sp, col_home, col_checker, col_about = st.columns([2, 4, 1, 2, 1])

    with col_logo:
        st.markdown(
            "<div style='padding:10px 0 4px 0; font-size:1.3rem; font-weight:800; color:#E87722;'>🔍 Jinggo Plag</div>",
            unsafe_allow_html=True,
        )

    with col_home:
        css_class = "nav-btn-active" if home_active else "nav-btn"
        st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
        if st.button("Home", key="nav_home"):
            navigate_to(ROUTE_HOME)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_checker:
        css_class = "nav-btn-active" if checker_active else "nav-btn"
        st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
        if st.button("Plagiarism Checker", key="nav_checker"):
            navigate_to(ROUTE_UPLOAD)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_about:
        css_class = "nav-btn-active" if about_active else "nav-btn"
        st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
        if st.button("About", key="nav_about"):
            navigate_to(ROUTE_ABOUT)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin:0 0 1rem 0; border:none; border-top:1.5px solid #E0E0E0;'>",
        unsafe_allow_html=True,
    )
