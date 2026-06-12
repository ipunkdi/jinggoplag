"""
Halaman Checker Detail (Step 4)
================================
Area inspeksi visual: side-by-side comparison dengan highlight kuning
pada baris kode yang memiliki fingerprint identik.

Layout:
    [Files of ProjectA: path/file_a.py]  |  [Files of ProjectB: path/file_b.py]
    [Baris kode...]  [similarity%]       |  [Baris kode...]  [similarity%]

Baris kuning = fingerprint cocok dengan pasangan file-nya.
Baris putih  = tidak ada kemiripan yang terdeteksi.
"""

import streamlit as st
import html as html_module

from services.highlighter import HighlightService, HighlightedLine


ROUTE_RESULT = "checker_result"


def render(navigate_to) -> None:
    """
    Merender halaman Detail.

    Args:
        navigate_to: Callback navigasi dari app.py
    """
    from pages.checker_upload import _render_step_indicator
    _render_step_indicator(current_step=4)

    file_pair  = st.session_state.get("selected_file_pair")
    comparison = st.session_state.get("selected_comparison")

    if file_pair is None or comparison is None:
        st.warning("Tidak ada file yang dipilih. Kembali ke halaman Result.")
        if st.button("← Kembali", key="btn_back_result"):
            navigate_to(ROUTE_RESULT)
        return

    st.markdown("<div style='padding-top: 1rem;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Header — judul dan average similarity
    # ----------------------------------------------------------------
    st.markdown(
        """
        <h2 style="
            text-align: center;
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: 3px;
            color: #1A1A1A;
            margin-bottom: 0.3rem;
        ">COMPARISON</h2>
        """,
        unsafe_allow_html=True,
    )

    from pages.checker_comparisons import _threshold_badge
    badge = _threshold_badge(file_pair.similarity, file_pair.threshold)
    st.markdown(
        f"""
        <p style="text-align:center; font-size:0.92rem; color:#555; margin-bottom:1.2rem;">
            Average Similarity: {badge}
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------------------
    # Ambil data fingerprint dan original source dari session_state
    # ----------------------------------------------------------------
    fingerprint_data = st.session_state.get("fingerprint_data", {})
    matched_hashes   = file_pair.matched_hashes

    fp_a = fingerprint_data.get(comparison.project_a, {}).get(file_pair.file_a)
    fp_b = fingerprint_data.get(comparison.project_b, {}).get(file_pair.file_b)

    projects_raw = st.session_state.get("projects_raw", {})
    original_a   = projects_raw.get(comparison.project_a, {}).get(file_pair.file_a, "")
    original_b   = projects_raw.get(comparison.project_b, {}).get(file_pair.file_b, "")

    # ----------------------------------------------------------------
    # Jalankan HighlightService
    # ----------------------------------------------------------------
    hl_svc = HighlightService()

    highlighted_a = hl_svc.highlight(
        original_text=original_a,
        hash_positions=fp_a.hash_positions if fp_a else [],
        matched_hashes=matched_hashes,
    )

    highlighted_b = hl_svc.highlight(
        original_text=original_b,
        hash_positions=fp_b.hash_positions if fp_b else [],
        matched_hashes=matched_hashes,
    )

    # Statistik highlight
    stats_a = HighlightService.compute_match_stats(highlighted_a)
    stats_b = HighlightService.compute_match_stats(highlighted_b)

    # ----------------------------------------------------------------
    # Side-by-side layout
    # ----------------------------------------------------------------
    col_a, col_divider, col_b = st.columns([10, 0.2, 10])

    # Path lengkap file
    full_path_a = f"{comparison.project_a}/{file_pair.file_a}"
    full_path_b = f"{comparison.project_b}/{file_pair.file_b}"

    with col_a:
        _render_code_panel(
            title=f"Files of {comparison.project_a}:",
            full_path=full_path_a,
            highlighted_lines=highlighted_a,
            similarity=file_pair.similarity,
            stats=stats_a,
            panel_id="panel_a",
        )

    with col_divider:
        st.markdown(
            "<div style='background:#DDDDDD; width:1px; min-height:400px; "
            "margin:0 auto;'></div>",
            unsafe_allow_html=True,
        )

    with col_b:
        _render_code_panel(
            title=f"Files of {comparison.project_b}:",
            full_path=full_path_b,
            highlighted_lines=highlighted_b,
            similarity=file_pair.similarity,
            stats=stats_b,
            panel_id="panel_b",
        )

    # ----------------------------------------------------------------
    # Legenda & navigasi bawah
    # ----------------------------------------------------------------
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    col_legend, col_back = st.columns([3, 1])
    with col_legend:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:1rem; font-size:0.82rem; color:#555;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <div style="width:16px; height:16px; background:#FFF176;
                                border:1px solid #F9A825; border-radius:3px;"></div>
                    <span>Fingerprint identik (matched)</span>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <div style="width:16px; height:16px; background:#FFFFFF;
                                border:1px solid #DDDDDD; border-radius:3px;"></div>
                    <span>Tidak ada kemiripan</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_back:
        if st.button("← Kembali ke Result", key="btn_back_to_result"):
            navigate_to(ROUTE_RESULT)


# ---------------------------------------------------------------------------
# Code Panel Renderer
# ---------------------------------------------------------------------------

def _render_code_panel(
    title: str,
    full_path: str,
    highlighted_lines: list[HighlightedLine],
    similarity: float,
    stats: dict,
    panel_id: str,
) -> None:
    """
    Merender satu panel kode (kiri atau kanan).

    Args:
        title:             Label header panel ("Files of ProjectA:")
        full_path:         Path lengkap file (misal: ProjectA/main.py)
        highlighted_lines: Output HighlightService
        similarity:        Persentase similarity file ini
        stats:             Output compute_match_stats
        panel_id:          ID unik untuk key widget (panel_a / panel_b)
    """
    # Header panel
    st.markdown(
        f"""
        <div style="
            border: 1px solid #CCCCCC;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 0.8rem;
            background: #F5F5F5;
            font-size: 0.8rem;
            color: #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div>
                <span style="font-weight:600; color:#E87722;">{title}</span><br>
                <span style="font-family:monospace; font-size:0.78rem; color:#555;">
                    {html_module.escape(full_path)}
                </span>
            </div>
            <div style="text-align:right;">
                <span style="font-weight:700; color:#D32F2F; font-size:0.9rem;">
                    {similarity:.1f}%
                </span><br>
                <span style="color:#888; font-size:0.72rem;">
                    {stats['matched_lines']}/{stats['total_lines']} baris
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Blok kode dengan highlight
    code_html = _build_code_html(highlighted_lines)

    st.markdown(
        f"""
        <div style="
            border: 1px solid #CCCCCC;
            border-radius: 0 0 8px 8px;
            overflow-x: auto;
            overflow-y: auto;
            max-height: 520px;
            background: #FFFFFF;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.78rem;
            line-height: 1.5;
        ">
            <table style="
                border-collapse: collapse;
                width: 100%;
                min-width: 300px;
            ">
                {code_html}
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_code_html(highlighted_lines: list[HighlightedLine]) -> str:
    """
    Membangun HTML tabel kode dengan highlight kuning pada baris matched.

    Setiap baris = satu <tr> dengan dua <td>:
    - td.line-num: nomor baris (abu)
    - td.line-code: konten kode (kuning jika is_match=True)

    Returns:
        String HTML berisi semua baris <tr>
    """
    rows: list[str] = []

    for line in highlighted_lines:
        bg_color = "#FFF176" if line.is_match else "#FFFFFF"
        num_bg   = "#FFF9C4" if line.is_match else "#F9F9F9"

        # Escape HTML entities di konten kode untuk keamanan
        safe_content = html_module.escape(line.content)

        # Ganti spasi ganda agar indentasi terlihat di HTML
        safe_content = safe_content.replace("  ", "&nbsp;&nbsp;")

        # Jika baris kosong, tampilkan non-breaking space agar baris memiliki tinggi
        if not safe_content:
            safe_content = "&nbsp;"

        row = (
            f"<tr>"
            f"<td style='"
            f"background:{num_bg}; color:#999; text-align:right; "
            f"padding:1px 8px 1px 4px; user-select:none; "
            f"border-right:1px solid #EEEEEE; min-width:32px; "
            f"font-size:0.72rem; vertical-align:top;"
            f"'>{line.line_number}</td>"
            f"<td style='"
            f"background:{bg_color}; padding:1px 8px; "
            f"white-space:pre; vertical-align:top;"
            f"'>{safe_content}</td>"
            f"</tr>"
        )
        rows.append(row)

    return "\n".join(rows)