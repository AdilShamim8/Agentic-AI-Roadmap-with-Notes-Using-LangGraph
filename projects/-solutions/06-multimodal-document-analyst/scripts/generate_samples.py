"""Generate sample PDFs for testing the Multimodal Document Analyst.

Each generated PDF contains:
  - Multiple pages of body text.
  - At least one embedded image (a matplotlib chart).
  - At least one table drawn with cell borders (so the table detector
    can find it).

Outputs three PDFs into `samples/`:
  - financial_report.pdf      (revenue / margins / a bar chart)
  - climate_brief.pdf         (temperature trends / a line chart / a table)
  - product_specs.pdf         (specs table + a polar-radar chart)
"""
from __future__ import annotations

import io
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import reportlab.lib.colors as colors
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table as RLTable,
    TableStyle,
)


OUT_DIR = Path(__file__).resolve().parents[1] / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use a CJK-safe font list for matplotlib (per project rule).
import matplotlib.font_manager as fm

try:
    fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
except Exception:  # noqa: BLE001
    pass
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ----------------------------------------------------------------------
# Chart helpers
# ----------------------------------------------------------------------
def _bar_chart() -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    years = ["2020", "2021", "2022", "2023", "2024"]
    revenue = [42, 51, 67, 88, 102]
    ax.bar(years, revenue, color="#4C72B0")
    ax.set_title("Annual Revenue (USD millions)")
    ax.set_ylabel("Revenue")
    ax.set_xlabel("Year")
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _line_chart() -> bytes:
    fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
    years = list(range(1880, 2025, 10))
    temps = [-0.2, -0.15, -0.1, 0.05, 0.2, 0.35, 0.6, 0.9, 1.2, 1.45, 1.55, 1.55, 1.6, 1.65, 1.7]
    ax.plot(years, temps, marker="o", color="#C44E52")
    ax.set_title("Global mean temperature anomaly (°C vs 1850-1900)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Anomaly (°C)")
    ax.grid(True, alpha=0.3)
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _radar_chart() -> bytes:
    categories = ["Battery", "Camera", "Speed", "Storage", "Display", "Price"]
    n = len(categories)
    angles = [i / float(n) * 2 * math.pi for i in range(n)]
    angles += angles[:1]
    values = [8, 7, 9, 6, 8, 7]
    values += values[:1]
    fig = plt.figure(figsize=(5, 4.2), constrained_layout=True)
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values, color="#55A868")
    ax.fill(angles, values, color="#55A868", alpha=0.3)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_title("Product scorecard (0-10)", pad=20)
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", dpi=120)
    plt.close(fig)
    return buf.getvalue()


# ----------------------------------------------------------------------
# PDF builders
# ----------------------------------------------------------------------
def _styles():
    ss = getSampleStyleSheet()
    return ss


def _img(b: bytes, width: float = 5 * inch) -> RLImage:
    buf = io.BytesIO(b)
    img = RLImage(buf)
    # Preserve aspect ratio.
    ratio = img.imageHeight / float(img.imageWidth)
    img.drawWidth = width
    img.drawHeight = width * ratio
    return img


def _table(rows: list[list[str]], col_widths: list[float] | None = None) -> RLTable:
    t = RLTable(rows, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#EEEEEE")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def build_financial_report(path: Path) -> None:
    ss = _styles()
    story = []
    story.append(Paragraph("Acme Corp. — Annual Financial Report 2024", ss["Title"]))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "This report summarises Acme Corp.'s financial performance for the fiscal year 2024. "
            "Total revenue reached <b>USD 102 million</b>, up 16% year-over-year from USD 88 million in 2023. "
            "Gross margin improved by 2.4 percentage points to 61.8%, driven primarily by a richer "
            "enterprise software mix and a one-time contract with Globex Corporation.",
            ss["BodyText"],
        )
    )
    story.append(Spacer(1, 14))
    story.append(Paragraph("Revenue trend", ss["Heading2"]))
    story.append(_img(_bar_chart()))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Operating expenses grew 9% to USD 41 million, with research and development "
            "representing the largest line item at USD 18 million. Sales and marketing "
            "totaled USD 14 million, and general & administrative expenses were USD 9 million. "
            "The company ended the year with USD 27 million in cash and equivalents.",
            ss["BodyText"],
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("Segment breakdown", ss["Heading2"]))
    story.append(
        Paragraph(
            "The following table shows the revenue contribution by segment for the last "
            "three fiscal years. The Enterprise SaaS segment has overtaken Professional "
            "Services as the largest contributor since 2023.",
            ss["BodyText"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        _table(
            [
                ["Segment", "2022 (USD m)", "2023 (USD m)", "2024 (USD m)"],
                ["Enterprise SaaS", "29.4", "41.0", "52.7"],
                ["Professional Services", "21.6", "26.3", "28.5"],
                ["Hardware", "10.5", "13.1", "14.2"],
                ["Training", "5.5", "7.6", "6.6"],
                ["Total", "67.0", "88.0", "102.0"],
            ],
            col_widths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
        )
    )
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "Outlook for 2025: management expects revenue between USD 118 and 124 million "
            "with gross margin holding in the 60-62% range. Capital expenditures are projected "
            "at USD 8 million, primarily for datacenter expansion in the EMEA region.",
            ss["BodyText"],
        )
    )
    SimpleDocTemplate(str(path), pagesize=letter).build(story)


def build_climate_brief(path: Path) -> None:
    ss = _styles()
    story = []
    story.append(Paragraph("Climate Brief 2024 — Global Temperature Trends", ss["Title"]))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Global mean surface temperature in 2024 was approximately <b>1.55 °C</b> above "
            "the 1850-1900 pre-industrial baseline, making 2024 the warmest year on record. "
            "This marks the first time annual warming has exceeded the 1.5 °C threshold "
            "highlighted in the Paris Agreement.",
            ss["BodyText"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Historical temperature anomaly", ss["Heading2"]))
    story.append(_img(_line_chart()))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Ocean heat content also reached a record high. The Arctic sea-ice extent minimum "
            "in September 2024 was the third-lowest on satellite record. The World Meteorological "
            "Organization notes that the last ten years (2015-2024) were the ten warmest on record.",
            ss["BodyText"],
        )
    )
    story.append(PageBreak())
    story.append(Paragraph("Regional anomalies", ss["Heading2"]))
    story.append(
        Paragraph(
            "The table below shows regional surface temperature anomalies for 2024 relative to "
            "the 1991-2020 baseline. Note that high-latitude regions warm significantly faster "
            "than the global mean — a phenomenon known as polar amplification.",
            ss["BodyText"],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        _table(
            [
                ["Region", "Anomaly (°C)", "Notes"],
                ["Arctic", "+3.2", "Polar amplification"],
                ["Antarctic", "+1.8", "Sea-ice loss accelerated"],
                ["Europe", "+1.5", "Hottest year on record"],
                ["Asia", "+1.3", "Heatwaves in South Asia"],
                ["North America", "+1.2", "Western heatwaves"],
                ["Africa", "+1.1", "Sahel drought"],
                ["Oceania", "+0.9", "Marine heatwave"],
                ["Global mean", "+1.0", "vs 1991-2020"],
            ],
            col_widths=[1.8 * inch, 1.4 * inch, 2.4 * inch],
        )
    )
    SimpleDocTemplate(str(path), pagesize=letter).build(story)


def build_product_specs(path: Path) -> None:
    ss = _styles()
    story = []
    story.append(Paragraph("Product Spec Sheet — Helios X1 Smartphone", ss["Title"]))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "The Helios X1 is the company's flagship smartphone for 2025. It features a 6.7-inch "
            "OLED display, a triple-camera array with a 50 MP primary sensor, and the third-generation "
            "Helios SoC fabricated on a 3 nm process.",
            ss["BodyText"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Scorecard", ss["Heading2"]))
    story.append(_img(_radar_chart()))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Specifications", ss["Heading2"]))
    story.append(
        _table(
            [
                ["Attribute", "Value"],
                ["Display", "6.7 in OLED, 1440 x 3200, 120 Hz"],
                ["SoC", "Helios G3 (3 nm)"],
                ["RAM", "12 GB LPDDR5X"],
                ["Storage", "256 GB / 512 GB / 1 TB UFS 4.0"],
                ["Battery", "5000 mAh, 100 W wired charging"],
                ["Rear camera", "50 MP main + 12 MP ultrawide + 10 MP 3x tele"],
                ["Front camera", "32 MP"],
                ["OS", "HeliosOS 15 (Android 15 based)"],
                ["Weight", "192 g"],
                ["IP rating", "IP68"],
                ["Launch price (USD)", "$899"],
            ],
            col_widths=[2.0 * inch, 3.6 * inch],
        )
    )
    SimpleDocTemplate(str(path), pagesize=letter).build(story)


def main() -> None:
    paths = [
        OUT_DIR / "financial_report.pdf",
        OUT_DIR / "climate_brief.pdf",
        OUT_DIR / "product_specs.pdf",
    ]
    build_financial_report(paths[0])
    build_climate_brief(paths[1])
    build_product_specs(paths[2])
    print(f"Generated {len(paths)} sample PDFs in {OUT_DIR}")
    for p in paths:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
