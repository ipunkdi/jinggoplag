"""
Navbar Component.

Komponen navigasi atas yang konsisten di semua halaman.
Layout: Logo | Home | Plagiarism Checker | About.

Dua kebutuhan desain yang diselesaikan di sini:

1. VERTICAL ALIGNMENT — logo (custom <div>) dan tombol (native st.button())
   punya box model yang berbeda secara default, sehingga rawan tidak
   sejajar. Solusi: beri height EKSPLISIT yang identik (44px) pada KEDUA
   jenis elemen, plus align-items:center pada baris flex itu sendiri.

2. ACTIVE STATE — alih-alih CSS class custom yang dibungkus lewat
   st.markdown() terpisah (TIDAK menghasilkan nesting DOM sungguhan,
   sudah dibuktikan tidak berfungsi sebelumnya), kita pakai parameter
   RESMI Streamlit `type="primary"` / `type="secondary"` pada st.button().
   Ini API publik yang stabil antar versi. Tampilan visualnya (warna
   solid bawaan tema) kita override lewat CSS yang menargetkan atribut
   `kind` pada elemen <button> — atribut struktural komponen dasar
   Streamlit, BUKAN hash class auto-generated yang rapuh.
"""

import streamlit as st

ROUTE_HOME        = "home"
ROUTE_UPLOAD      = "checker_upload"
ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_ABOUT       = "about"

_NAVBAR_ROW_ANCHOR = (
    'div[data-testid="stHorizontalBlock"]:has(div.navbar-logo)'
)

_NAVBAR_CSS = f"""
<style>
/* Sejajarkan SEMUA child (logo + tombol) secara vertikal di baris navbar. */
{_NAVBAR_ROW_ANCHOR} {{
    align-items: center !important;
}}

/* Logo: height eksplisit identik dengan tombol, teks center vertikal. */
.navbar-logo {{
    display: flex;
    align-items: center;
    height: 44px;
    font-size: 1.3rem;
    font-weight: 800;
    color: #E87722;
    white-space: nowrap;
}}

/* Tombol navbar: height eksplisit sama dengan logo (44px), teks tidak wrap. */
{_NAVBAR_ROW_ANCHOR} div[data-testid="stButton"] > button {{
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    min-width: max-content !important;
    box-sizing: border-box !important;
}}

/* Nav AKTIF (type="primary"): teks oranye bold, tanpa background/border. */
{_NAVBAR_ROW_ANCHOR} button[kind="primary"],
{_NAVBAR_ROW_ANCHOR} [data-testid="stBaseButton-primary"] {{
    background-color: transparent !important;
    border: none !important;
    color: #E87722 !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}}
{_NAVBAR_ROW_ANCHOR} button[kind="primary"]:hover,
{_NAVBAR_ROW_ANCHOR} [data-testid="stBaseButton-primary"]:hover {{
    background-color: transparent !important;
    color: #E87722 !important;
    border: none !important;
}}

/* Nav TIDAK AKTIF (type="secondary"): teks netral, tanpa background/border. */
{_NAVBAR_ROW_ANCHOR} button[kind="secondary"],
{_NAVBAR_ROW_ANCHOR} [data-testid="stBaseButton-secondary"] {{
    background-color: transparent !important;
    border: none !important;
    color: #333333 !important;
    font-weight: 400 !important;
    box-shadow: none !important;
}}
{_NAVBAR_ROW_ANCHOR} button[kind="secondary"]:hover,
{_NAVBAR_ROW_ANCHOR} [data-testid="stBaseButton-secondary"]:hover {{
    background-color: transparent !important;
    color: #E87722 !important;
    border: none !important;
}}
</style>
"""


def render_navbar(navigate_to) -> None:
    """
    Render navbar horizontal dengan logo dan tiga tautan navigasi.

    Tautan yang sesuai dengan halaman aktif saat ini ditampilkan dengan
    teks oranye bold (type="primary"); yang lain netral (type="secondary").

    Args:
        navigate_to: Callback fungsi dari app.py untuk berpindah halaman.
    """
    current_route = st.session_state.get("current_route", ROUTE_HOME)

    home_active    = current_route == ROUTE_HOME
    checker_active = current_route in (
        ROUTE_UPLOAD, ROUTE_COMPARISONS, "checker_result", "checker_detail"
    )
    about_active   = current_route == ROUTE_ABOUT

    st.markdown(_NAVBAR_CSS, unsafe_allow_html=True)

    col_logo, _, col_home, col_checker, col_about = st.columns([2, 4, 1.3, 2.4, 1.3])

    with col_logo:
        st.markdown(
            "<div class='navbar-logo'>🔍 Jinggo Plag</div>",
            unsafe_allow_html=True,
        )

    with col_home:
        if st.button(
            "Home", key="nav_home", use_container_width=True,
            type="primary" if home_active else "secondary",
        ):
            navigate_to(ROUTE_HOME)

    with col_checker:
        if st.button(
            "Plagiarism Checker", key="nav_checker", use_container_width=True,
            type="primary" if checker_active else "secondary",
        ):
            navigate_to(ROUTE_UPLOAD)

    with col_about:
        if st.button(
            "About", key="nav_about", use_container_width=True,
            type="primary" if about_active else "secondary",
        ):
            navigate_to(ROUTE_ABOUT)

    st.markdown(
        "<hr style='margin:0 0 1rem 0; border:none; border-top:1.5px solid #E0E0E0;'>",
        unsafe_allow_html=True,
    )
