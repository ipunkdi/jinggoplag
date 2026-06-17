"""
Halaman Home.

Single-screen landing page dengan hero section dan tombol CTA "ANALYSIS NOW".

CATATAN ARSITEKTUR PENTING — Mengapa TIDAK menggunakan display:flex
pada .main .block-container:
Navbar (komponen terpisah) dan konten Home dirender ke KONTAINER YANG SAMA
(.main .block-container), karena Streamlit tidak memisahkan navbar ke
elemen DOM tersendiri. Memaksa display:flex + justify-content:center pada
kontainer tersebut akan mengubah konteks layout SELURUH anak elemen di
dalamnya — termasuk baris kolom navbar — yang dapat menyebabkan kolom
sempit (Home/About) menyusut dan teks-nya wrap, sementara kolom lebar
(Plagiarism Checker) tetap aman. Sebagai gantinya, single-screen look
dicapai dengan padding-top berbasis vh pada wrapper LOKAL saja, tanpa
mengubah properti flex/justify-content kontainer bersama.
"""

import streamlit as st

_HOME_CSS = """
<style>
.main .block-container {
    overflow: hidden !important;
}
div[data-testid="stButton"] > button {
    background-color: #FFFFFF !important;
    color: #1A1A1A !important;
    border: 2.5px solid #1A1A1A !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 1px !important;
    padding: 0.55rem 2rem !important;
}
div[data-testid="stButton"] > button:hover {
    background-color: #E87722 !important;
    border-color: #E87722 !important;
    color: #FFFFFF !important;
}
</style>
"""


def render(navigate_to) -> None:
    """
    Render halaman Home.

    Args:
        navigate_to: Callback untuk berpindah ke halaman lain.
    """
    st.markdown(_HOME_CSS, unsafe_allow_html=True)

    # Padding berbasis vh untuk memvisualkan hero content di tengah viewport,
    # TANPA mengubah display/flex pada .block-container (lihat catatan di atas).
    st.markdown("<div style='padding-top: 10vh;'></div>", unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 3, 1])

    with col_center:
        st.markdown(
            """
            <h1 style="
                text-align:center;
                font-size:2.6rem;
                font-weight:900;
                color:#1A1A1A;
                line-height:1.2;
                margin-bottom:1.2rem;
            ">
                DETECT SOURCE CODE PLAGIARISM<br>QUICKLY &amp; ACCURATELY
            </h1>
            <p style="
                text-align:center;
                font-size:1.05rem;
                color:#555555;
                line-height:1.7;
                margin-bottom:2.5rem;
            ">
                Compare PHP, Dart, or Python projects using the<br>
                <strong>Winnowing Fingerprinting</strong> &amp;
                <strong>Rolling Hash Rabin-Karp</strong> Algorithms
            </p>
            """,
            unsafe_allow_html=True,
        )

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("ANALYSIS NOW", key="cta_home_btn", use_container_width=True):
                navigate_to("checker_upload")
