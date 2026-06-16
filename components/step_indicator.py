"""
Step Indicator Component
========================
Komponen breadcrumb wizard yang digunakan bersama oleh semua halaman
Plagiarism Checker (Upload, Comparisons, Result, Detail).
"""

import streamlit as st


def render_step_indicator(current_step: int) -> None:
    """
    Render breadcrumb step indicator di bagian atas halaman checker.

    Args:
        current_step: Nomor step aktif (1=Upload, 2=Comparisons, 3=Result, 4=Detail).
    """
    steps = [
        (1, "Upload"),
        (2, "Comparisons"),
        (3, "Result"),
        (4, "Detail"),
    ]
    parts = []
    for step_num, label in steps:
        if step_num == current_step:
            span = (
                f'<span style="color:#E87722;font-weight:700;">'
                f"Step {step_num}: {label}</span>"
            )
        elif step_num < current_step:
            span = (
                f'<span style="color:#BBBBBB;text-decoration:line-through;">'
                f"Step {step_num}: {label}</span>"
            )
        else:
            span = (
                f'<span style="color:#CCCCCC;">'
                f"Step {step_num}: {label}</span>"
            )
        parts.append(span)

    separator = ' <span style="color:#CCCCCC;margin:0 0.4rem;">›</span> '
    st.markdown(
        f'<div style="text-align:center;font-size:0.88rem;padding:0.4rem 0;">'
        f"{separator.join(parts)}</div>",
        unsafe_allow_html=True,
    )
