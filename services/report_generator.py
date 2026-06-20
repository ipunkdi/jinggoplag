"""
ReportGeneratorService
=======================
Menghasilkan laporan PDF dari hasil deteksi plagiarisme, menggunakan
reportlab (pure-Python, tanpa dependensi sistem seperti Cairo/Pango —
aman untuk deployment di Streamlit Cloud atau server minimal).

Dua jenis laporan didukung:

1. SUMMARY REPORT  — seluruh pasangan project dalam satu .zip (laporan
   kelas penuh), diurutkan dari similarity tertinggi. Cocok untuk
   dilampirkan sebagai bukti pemeriksaan satu angkatan/kelas.

2. DETAIL REPORT   — rincian satu pasangan project beserta breakdown
   per file, cocok untuk dilampirkan saat berdiskusi dengan mahasiswa
   tertentu yang terindikasi tinggi.

Tidak ada operasi tulis ke disk — seluruh PDF dihasilkan sebagai bytes
di memori (BytesIO), konsisten dengan prinsip privacy-by-design sistem.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ALGORITHM_PARAMS = {
    "k":   5,
    "w":   4,
    "base": 256,
    "mod": "1.000.000.007",
}

THRESHOLD_COLORS = {
    "High":     (colors.HexColor("#FFEBEE"), colors.HexColor("#D32F2F")),
    "Moderate": (colors.HexColor("#FFF3E0"), colors.HexColor("#E87722")),
    "Low":      (colors.HexColor("#E8F5E9"), colors.HexColor("#2E7D32")),
}

BRAND_ORANGE = colors.HexColor("#E87722")
DARK_TEXT    = colors.HexColor("#1A1A1A")
GRAY_TEXT    = colors.HexColor("#666666")
LIGHT_BORDER = colors.HexColor("#DDDDDD")


class ReportGeneratorService:
    """Menghasilkan laporan PDF deteksi plagiarisme dalam bentuk bytes."""

    def __init__(self) -> None:
        """Inisialisasi style paragraf yang dipakai berulang di seluruh laporan."""
        base_styles = getSampleStyleSheet()

        self.style_title = ParagraphStyle(
            "ReportTitle", parent=base_styles["Title"],
            fontSize=18, textColor=DARK_TEXT, spaceAfter=4,
        )
        self.style_subtitle = ParagraphStyle(
            "ReportSubtitle", parent=base_styles["Normal"],
            fontSize=10, textColor=GRAY_TEXT, spaceAfter=14,
        )
        self.style_section_header = ParagraphStyle(
            "SectionHeader", parent=base_styles["Heading2"],
            fontSize=13, textColor=DARK_TEXT, spaceBefore=14, spaceAfter=8,
        )
        self.style_body = ParagraphStyle(
            "ReportBody", parent=base_styles["Normal"],
            fontSize=9.5, textColor=DARK_TEXT, leading=14,
        )
        self.style_meta_label = ParagraphStyle(
            "MetaLabel", parent=base_styles["Normal"],
            fontSize=9, textColor=GRAY_TEXT,
        )
        self.style_footer = ParagraphStyle(
            "Footer", parent=base_styles["Normal"],
            fontSize=8, textColor=GRAY_TEXT,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_summary_report(self, comparison_results: list) -> bytes:
        """
        Hasilkan laporan ringkasan seluruh pasangan project.

        Args:
            comparison_results: list[ComparisonResult] dari SimilarityService.

        Returns:
            Konten PDF sebagai bytes, siap dikirim via st.download_button.
        """
        buffer = io.BytesIO()
        doc    = self._build_document(buffer)

        story: list = []
        story.extend(self._build_header(
            "Laporan Ringkasan Deteksi Plagiarisme",
            f"{len(comparison_results)} pasangan project dianalisis",
        ))
        story.extend(self._build_metadata_block(comparison_results))
        story.extend(self._build_statistics_block(comparison_results))
        story.append(Paragraph("Rincian Seluruh Pasangan", self.style_section_header))
        story.append(self._build_summary_table(comparison_results))
        story.extend(self._build_footer_note())

        doc.build(story, onFirstPage=self._draw_page_footer,
                  onLaterPages=self._draw_page_footer)
        return buffer.getvalue()

    def generate_detail_report(self, comparison) -> bytes:
        """
        Hasilkan laporan rincian satu pasangan project.

        Args:
            comparison: Satu instance ComparisonResult dari SimilarityService.

        Returns:
            Konten PDF sebagai bytes, siap dikirim via st.download_button.
        """
        buffer = io.BytesIO()
        doc    = self._build_document(buffer)

        story: list = []
        story.extend(self._build_header(
            "Laporan Detail Perbandingan Project",
            f"{comparison.project_a}  vs  {comparison.project_b}",
        ))
        story.extend(self._build_overall_score_block(comparison))
        story.append(Paragraph(
            f"Rincian Per File ({len(comparison.file_pairs)} pasangan)",
            self.style_section_header,
        ))
        story.append(self._build_file_pairs_table(comparison.file_pairs))
        story.extend(self._build_footer_note())

        doc.build(story, onFirstPage=self._draw_page_footer,
                  onLaterPages=self._draw_page_footer)
        return buffer.getvalue()

    # ── Document setup ───────────────────────────────────────────────────────

    @staticmethod
    def _build_document(buffer: io.BytesIO) -> SimpleDocTemplate:
        """Buat SimpleDocTemplate dengan margin dan ukuran halaman standar."""
        return SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
            leftMargin=2.0 * cm, rightMargin=2.0 * cm,
            title="Laporan Jinggo Plag",
        )

    # ── Reusable story blocks ─────────────────────────────────────────────────

    def _build_header(self, title: str, subtitle: str) -> list:
        """Bangun blok judul laporan dengan logo teks dan subjudul."""
        return [
            Paragraph("🔍 Jinggo Plag", ParagraphStyle(
                "Brand", fontSize=11, textColor=BRAND_ORANGE,
                fontName="Helvetica-Bold", spaceAfter=10,
            )),
            Paragraph(title, self.style_title),
            Paragraph(subtitle, self.style_subtitle),
        ]

    def _build_metadata_block(self, comparison_results: list) -> list:
        """Bangun tabel metadata: tanggal, jumlah project, parameter algoritma."""
        all_projects: set = set()
        for comp in comparison_results:
            all_projects.add(comp.project_a)
            all_projects.add(comp.project_b)

        generated_at = datetime.now().strftime("%d %B %Y, %H:%M")

        rows = [
            ["Tanggal Analisis", generated_at],
            ["Jumlah Project", str(len(all_projects))],
            ["Jumlah Pasangan", str(len(comparison_results))],
            [
                "Parameter Algoritma",
                f"k={ALGORITHM_PARAMS['k']}, w={ALGORITHM_PARAMS['w']}, "
                f"base={ALGORITHM_PARAMS['base']}, mod={ALGORITHM_PARAMS['mod']}",
            ],
            ["Threshold", "Rendah < 30%  |  Moderat 30-80%  |  Tinggi > 80%"],
        ]

        table = Table(rows, colWidths=[4.5 * cm, 12 * cm])
        table.setStyle(TableStyle([
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",    (0, 0), (0, -1),  GRAY_TEXT),
            ("TEXTCOLOR",    (1, 0), (1, -1),  DARK_TEXT),
            ("FONTNAME",     (0, 0), (0, -1),  "Helvetica-Bold"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ]))

        return [table, Spacer(1, 12)]

    def _build_statistics_block(self, comparison_results: list) -> list:
        """Bangun ringkasan jumlah pasangan per kategori threshold."""
        high_count = sum(1 for r in comparison_results if r.threshold == "High")
        mod_count  = sum(1 for r in comparison_results if r.threshold == "Moderate")
        low_count  = sum(1 for r in comparison_results if r.threshold == "Low")

        rows = [["Tinggi", "Moderat", "Rendah"], [str(high_count), str(mod_count), str(low_count)]]
        table = Table(rows, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        table.setStyle(TableStyle([
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("FONTNAME",      (0, 1), (-1, 1),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 1), (-1, 1),  14),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND",    (0, 0), (0, 1),   THRESHOLD_COLORS["High"][0]),
            ("TEXTCOLOR",     (0, 0), (0, 1),   THRESHOLD_COLORS["High"][1]),
            ("BACKGROUND",    (1, 0), (1, 1),   THRESHOLD_COLORS["Moderate"][0]),
            ("TEXTCOLOR",     (1, 0), (1, 1),   THRESHOLD_COLORS["Moderate"][1]),
            ("BACKGROUND",    (2, 0), (2, 1),   THRESHOLD_COLORS["Low"][0]),
            ("TEXTCOLOR",     (2, 0), (2, 1),   THRESHOLD_COLORS["Low"][1]),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX",           (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
        ]))

        return [table, Spacer(1, 10)]

    def _build_summary_table(self, comparison_results: list) -> Table:
        """Bangun tabel utama: seluruh pasangan project dengan badge threshold."""
        header = ["#", "Project A", "Project B", "Similarity", "Kategori"]
        rows: list = [header]

        for idx, comp in enumerate(comparison_results, start=1):
            rows.append([
                str(idx),
                Paragraph(self._truncate(comp.project_a, 38), self.style_body),
                Paragraph(self._truncate(comp.project_b, 38), self.style_body),
                f"{comp.similarity:.1f}%",
                comp.threshold,
            ])

        table = Table(rows, colWidths=[1 * cm, 5.7 * cm, 5.7 * cm, 2.3 * cm, 2.3 * cm], repeatRows=1)
        style_commands = self._base_table_style()

        for row_idx, comp in enumerate(comparison_results, start=1):
            bg, fg = THRESHOLD_COLORS.get(comp.threshold, (colors.white, DARK_TEXT))
            style_commands.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), fg))
            style_commands.append(("FONTNAME",  (4, row_idx), (4, row_idx), "Helvetica-Bold"))
            style_commands.append(("BACKGROUND", (3, row_idx), (4, row_idx), bg))

        table.setStyle(TableStyle(style_commands))
        return table

    def _build_overall_score_block(self, comparison) -> list:
        """Bangun blok skor keseluruhan untuk laporan detail satu pasangan."""
        bg, fg = THRESHOLD_COLORS.get(comparison.threshold, (colors.white, DARK_TEXT))

        rows = [[
            f"Average Similarity: {comparison.similarity:.1f}% ({comparison.threshold})"
        ]]
        table = Table(rows, colWidths=[16.5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TEXTCOLOR",     (0, 0), (-1, -1), fg),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 12),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        return [table, Spacer(1, 10)]

    def _build_file_pairs_table(self, file_pairs: list) -> Table:
        """Bangun tabel rincian pasangan file dalam satu perbandingan project."""
        header = ["#", "File A", "File B", "Similarity", "Kategori"]
        rows: list = [header]

        for idx, fp in enumerate(file_pairs, start=1):
            rows.append([
                str(idx),
                Paragraph(self._truncate(fp.file_a, 36), self.style_body),
                Paragraph(self._truncate(fp.file_b, 36), self.style_body),
                f"{fp.similarity:.1f}%",
                fp.threshold,
            ])

        table = Table(rows, colWidths=[1 * cm, 5.7 * cm, 5.7 * cm, 2.3 * cm, 2.3 * cm], repeatRows=1)
        style_commands = self._base_table_style()

        for row_idx, fp in enumerate(file_pairs, start=1):
            bg, fg = THRESHOLD_COLORS.get(fp.threshold, (colors.white, DARK_TEXT))
            style_commands.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), fg))
            style_commands.append(("FONTNAME",  (4, row_idx), (4, row_idx), "Helvetica-Bold"))
            style_commands.append(("BACKGROUND", (3, row_idx), (4, row_idx), bg))

        table.setStyle(TableStyle(style_commands))
        return table

    def _build_footer_note(self) -> list:
        """Bangun catatan kaki metodologis di akhir laporan."""
        note = (
            "Laporan ini dihasilkan otomatis menggunakan algoritma Winnowing "
            "Fingerprinting dengan Rolling Hash Rabin-Karp dan Jaccard Similarity. "
            "Persentase kemiripan mencerminkan kesamaan leksikal source code "
            "setelah preprocessing (penghapusan komentar, whitespace, dan case "
            "folding), dan perlu diverifikasi manual sebelum dijadikan dasar "
            "keputusan akademik."
        )
        return [Spacer(1, 16), Paragraph(note, self.style_footer)]

    # ── Low-level helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _base_table_style() -> list:
        """Style dasar yang dipakai bersama oleh tabel ringkasan dan detail."""
        return [
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK_TEXT),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
            ("ALIGN",         (3, 0), (4, -1),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW",     (0, 0), (-1, 0),  1, DARK_TEXT),
            ("LINEBELOW",     (0, 1), (-1, -1), 0.5, LIGHT_BORDER),
        ]

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Potong teks panjang dengan ellipsis agar tidak merusak layout tabel."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    @staticmethod
    def _draw_page_footer(canvas, doc) -> None:  # noqa: ARG004
        """Gambar nomor halaman dan label brand di footer setiap halaman."""
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY_TEXT)
        canvas.drawString(2 * cm, 1.2 * cm, "Dihasilkan oleh Jinggo Plag")
        canvas.drawRightString(
            A4[0] - 2 * cm, 1.2 * cm, f"Halaman {doc.page}"
        )
        canvas.restoreState()
