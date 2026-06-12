"""
Halaman Home — Fixed
====================
Perbaikan:
- Single-screen layout: non-scrollable, semua konten fit dalam viewport
- CTA tanpa perlu scroll
"""
import streamlit as st

def render(navigate_to) -> None:
    # CSS: fix viewport height, non-scrollable, center content
    st.markdown("""
    <style>
    /* Non-scrollable single viewport for home */
    .main .block-container {
        overflow: hidden !important;
        height: calc(100vh - 120px) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        padding-top: 0 !important;
    }
    /* CTA button styling */
    div[data-testid="stButton"][id*="cta_home"] > button,
    #btn-cta-home + div > button {
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
        border: 2.5px solid #1A1A1A !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 1px !important;
        padding: 0.55rem 2rem !important;
    }
    div[data-testid="stButton"][id*="cta_home"] > button:hover,
    #btn-cta-home + div > button:hover {
        background-color: #E87722 !important;
        border-color: #E87722 !important;
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_center, _ = st.columns([1, 3, 1])

    with col_center:
        st.markdown("""
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
        """, unsafe_allow_html=True)

        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            if st.button("ANALYSIS NOW", key="cta_home_btn", use_container_width=True):
                navigate_to("checker_upload")
