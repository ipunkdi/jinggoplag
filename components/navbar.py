"""
Navbar Component.

Komponen navigasi atas yang konsisten di semua halaman.
Layout: Logo | Home | Plagiarism Checker | About.

CATATAN ARSITEKTUR — Targeting CSS via :has():
Membungkus tombol dengan <div class="..."> di satu st.markdown() lalu
menutupnya di st.markdown() lain TIDAK menghasilkan nesting DOM yang
sebenarnya — setiap st.markdown() membuat elemen container-nya sendiri
sebagai sibling, bukan parent. Selector seperti
".nav-btn > div[data-testid='stButton'] > button" karena itu TIDAK PERNAH
cocok. Sebagai gantinya, kita gunakan selector :has() yang menjangkar pada
baris kolom navbar itu sendiri (mendeteksi span oranye "Jinggo Plag"),
lalu menata SEMUA tombol di dalam baris tersebut — teknik yang sama yang
sudah bekerja untuk sticky positioning di styles/main.css.
"""

import streamlit as st

ROUTE_HOME        = "home"
ROUTE_UPLOAD      = "checker_upload"
ROUTE_COMPARISONS = "checker_comparisons"
ROUTE_ABOUT       = "about"

_NAVBAR_CSS = """
<style>
/* Cegah teks tombol navbar membungkus baris kedua, apa pun lebar kolomnya. */
div[data-testid="stHorizontalBlock"]:has(
    div[data-testid="stMarkdownContainer"] span[style*="E87722"]
) div[data-testid="stButton"] > button {
    white-space: nowrap !important;
    min-width: max-content !important;
}
</style>
"""


def render_navbar(navigate_to) -> None:
    """
    Render navbar horizontal dengan logo dan tiga tautan navigasi.

    Args:
        navigate_to: Callback fungsi dari app.py untuk berpindah halaman.
    """
    st.markdown(_NAVBAR_CSS, unsafe_allow_html=True)

    col_logo, _, col_home, col_checker, col_about = st.columns([2, 4, 1.3, 2.4, 1.3])

    with col_logo:
        st.markdown(
            "<div style='padding:10px 0 4px 0; font-size:1.3rem; "
            "font-weight:800; color:#E87722;'>🔍 Jinggo Plag</div>",
            unsafe_allow_html=True,
        )

    with col_home:
        if st.button("Home", key="nav_home", use_container_width=True):
            navigate_to(ROUTE_HOME)

    with col_checker:
        if st.button("Plagiarism Checker", key="nav_checker", use_container_width=True):
            navigate_to(ROUTE_UPLOAD)

    with col_about:
        if st.button("About", key="nav_about", use_container_width=True):
            navigate_to(ROUTE_ABOUT)

    st.markdown(
        "<hr style='margin:0 0 1rem 0; border:none; border-top:1.5px solid #E0E0E0;'>",
        unsafe_allow_html=True,
    )
