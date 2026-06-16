"""
Halaman About.

Halaman statis dokumentasi teknis sistem.
Konten: The Science (flowchart), The Process (5 tahap), Developer.
"""

import streamlit as st


def render(navigate_to) -> None:  # noqa: ARG001
    """
    Render halaman About.

    Args:
        navigate_to: Callback navigasi (tidak digunakan di halaman statis ini).
    """
    st.markdown("<div style='padding-top: 1.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-size:1.4rem;font-weight:800;color:#1A1A1A;"
        "margin-bottom:1.2rem;'>The Science</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(_flowchart_svg(), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:2.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-size:1.4rem;font-weight:800;color:#1A1A1A;"
        "margin-bottom:1rem;'>The Process</h2>",
        unsafe_allow_html=True,
    )

    steps = [
        (
            "Extract .zip &amp; filter file",
            "Membuka arsip .zip dan menyaring hanya file berekstensi "
            "<code>.php</code>, <code>.dart</code>, dan <code>.py</code>.",
        ),
        (
            "Preprocess source code",
            "Menghapus semua komentar (bahasa-spesifik), whitespace, dan newline, "
            "lalu menerapkan <em>case folding</em> ke huruf kecil.",
        ),
        (
            "Generate &amp; select fingerprints",
            "Membentuk k-gram (k=5), menghitung hash dengan "
            "<strong>Rolling Hash Rabin-Karp</strong> (Base=256, Mod=1.000.000.007), "
            "lalu menyeleksi minimum per window (w=4) dengan <strong>Winnowing</strong>.",
        ),
        (
            "Compare fingerprints",
            "Membandingkan set fingerprint antar semua pasangan proyek menggunakan "
            "<strong>Jaccard Similarity</strong>: J(A,B) = |A∩B| / |A∪B| "
            "dengan strategi <em>Best Match Only</em>.",
        ),
        (
            "Highlight matches",
            "Memetakan hash yang cocok kembali ke posisi baris di source code asli "
            "(<em>reverse mapping</em>) dan menyorot dengan warna kuning.",
        ),
    ]

    for i, (title, desc) in enumerate(steps, start=1):
        st.markdown(
            f"""
            <div style="display:flex; gap:1rem; margin-bottom:1rem; align-items:flex-start;">
                <div style="min-width:32px; height:32px; background:#E87722; color:#FFFFFF;
                            border-radius:50%; display:flex; align-items:center;
                            justify-content:center; font-weight:800; font-size:0.9rem;
                            flex-shrink:0; margin-top:2px;">{i}</div>
                <div>
                    <div style="font-weight:700; color:#1A1A1A; margin-bottom:2px;">{title}</div>
                    <div style="font-size:0.88rem; color:#555; line-height:1.6;">{desc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:2.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="border-top:1.5px solid #EEEEEE; padding-top:1.5rem;">
            <h2 style="font-size:1.4rem; font-weight:800; color:#1A1A1A;
                       margin-bottom:0.5rem;">Developer</h2>
            <p style="font-size:1rem; color:#333;">
                <strong>Dafa Ifaldi</strong><br>
                <span style="font-size:0.88rem; color:#777;">
                    Politeknik Negeri Banyuwangi
                </span>
            </p>
            <p style="font-size:0.82rem; color:#AAAAAA; margin-top:1rem;">
                Sistem Deteksi Plagiarisme Source Code Berbasis Web &mdash;
                Winnowing Fingerprinting &amp; Rolling Hash Rabin-Karp
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _flowchart_svg() -> str:
    """
    Bangun flowchart algoritma sebagai SVG inline.

    Satu baris horizontal kiri ke kanan:
    Project Root → Preprocessing → K-Gram → Rolling Hash → Winnowing → Jaccard
    """
    dark  = "#1A1A1A"
    arrow = "#555555"
    white = "#FFFFFF"
    rx, ry = 62, 27

    nodes = [
        (68,  50, "Project Root",  "(.zip)"),
        (210, 50, "Preprocessing", "Source Code"),
        (352, 50, "Processing",    "K-Gram"),
        (494, 50, "Rolling Hash",  "Rabin-Karp"),
        (636, 50, "Winnowing",     "Fingerprinting"),
        (778, 50, "Statistical",   "Measure (Jaccard)"),
    ]

    parts: list = []
    parts.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 100" '
        'width="100%" style="max-width:900px;margin:0 auto;display:block;">'
    )
    parts.append(
        "<defs>"
        f'<marker id="ah" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">'
        f'<polygon points="0 0,7 2.5,0 5" fill="{arrow}"/>'
        "</marker>"
        "</defs>"
    )

    for cx, cy, _, _ in nodes:
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'fill="{white}" stroke="{dark}" stroke-width="1.5"/>'
        )

    for cx, cy, line1, line2 in nodes:
        parts.append(
            f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" '
            f'font-size="10" font-family="sans-serif" fill="{dark}">{line1}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 9}" text-anchor="middle" '
            f'font-size="10" font-family="sans-serif" fill="{dark}">{line2}</text>'
        )

    for i in range(len(nodes) - 1):
        cx1, cy1 = nodes[i][0], nodes[i][1]
        cx2, cy2 = nodes[i + 1][0], nodes[i + 1][1]
        parts.append(
            f'<line x1="{cx1 + rx}" y1="{cy1}" x2="{cx2 - rx}" y2="{cy2}" '
            f'stroke="{arrow}" stroke-width="1.5" marker-end="url(#ah)"/>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
