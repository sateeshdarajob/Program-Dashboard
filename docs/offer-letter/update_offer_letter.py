#!/usr/bin/env python3
"""Update offer letter designation and CTC from 36L to 47L using the same salary mapping."""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf as fitz

# Same mapping as the 36,00,000 structure:
# - Basic ≈ 36.131% of monthly CTC
# - HRA = 60% of Basic
# - Employer PF = 12% of Basic
# - Gratuity = 6.5% of Basic
# - LTA keeps the same ratio to Basic (~18.919%)
# - Conveyance (Flexi Basket) is the residual so monthly components sum to CTC
OLD_MONTHLY_CTC = 300_000
OLD_BASIC = 108_393
OLD_LTA = 20_507
NEW_ANNUAL_CTC = 4_700_000
NEW_MONTHLY_CTC = round(NEW_ANNUAL_CTC / 12)  # 3,91,667


def inr(n: int) -> str:
    """Format integer in Indian grouping (e.g. 141513 -> 1,41,513)."""
    s = str(int(n))
    if len(s) <= 3:
        return s
    result = s[-3:]
    s = s[:-3]
    while s:
        result = f"{s[-2:]},{result}"
        s = s[:-2]
    return result


def compute_salary() -> dict[str, tuple[int, int]]:
    factor = NEW_ANNUAL_CTC / (OLD_MONTHLY_CTC * 12)
    basic_m = round(OLD_BASIC * factor)
    lta_m = round(basic_m * (OLD_LTA / OLD_BASIC))
    hra_m = round(basic_m * 0.60)
    pf_m = round(basic_m * 0.12)
    gratuity_m = round(basic_m * 0.065)
    conveyance_m = NEW_MONTHLY_CTC - (basic_m + lta_m + hra_m + pf_m + gratuity_m)
    fixed_m = basic_m + lta_m + hra_m + conveyance_m
    assert fixed_m + pf_m + gratuity_m == NEW_MONTHLY_CTC

    def both(monthly: int, annual: int | None = None) -> tuple[int, int]:
        return monthly, monthly * 12 if annual is None else annual

    return {
        "basic": both(basic_m),
        "lta": both(lta_m),
        "hra": both(hra_m),
        "conveyance": both(conveyance_m),
        "fixed": both(fixed_m),
        "pf": both(pf_m),
        "gratuity": both(gratuity_m),
        # Annual CTC forced to the stated package amount (47,00,000).
        "gross": both(NEW_MONTHLY_CTC, NEW_ANNUAL_CTC),
        "ctc": both(NEW_MONTHLY_CTC, NEW_ANNUAL_CTC),
    }


FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"

def _insert_centered(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    *,
    fontsize: float,
    bold: bool,
) -> None:
    fontfile = FONT_BOLD if bold else FONT_REG
    font = fitz.Font(fontfile=fontfile)
    text_w = font.text_length(text, fontsize=fontsize)
    x = rect.x0 + (rect.width - text_w) / 2
    baseline = rect.y0 + fontsize
    page.insert_text(
        (x, baseline),
        text,
        fontsize=fontsize,
        fontfile=fontfile,
        fontname="NotoSansBold" if bold else "NotoSans",
        color=(0, 0, 0),
    )


def _apply_text_only_redactions(page: fitz.Page) -> None:
    """Remove redacted text only — keep gray row fills and watermark image."""
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE,
        graphics=fitz.PDF_REDACT_LINE_ART_NONE,
        text=fitz.PDF_REDACT_TEXT_REMOVE,
    )


def replace_centered(
    page: fitz.Page,
    old: str,
    new: str,
    *,
    fontsize: float,
    bold: bool = False,
    occurrence: int | None = None,
) -> None:
    """Replace one value, preserving gray row / watermark backgrounds."""
    hits = page.search_for(old)
    if not hits:
        raise RuntimeError(f"Could not find {old!r} on page {page.number + 1}")
    if occurrence is not None:
        hits = [hits[occurrence]]
    inserts: list[tuple[fitz.Rect, str, float, bool]] = []
    for rect in hits:
        tight = fitz.Rect(rect.x0 - 0.6, rect.y0 + 0.6, rect.x1 + 0.6, rect.y1 - 0.6)
        # No fill: do not paint white boxes over gray rows / watermark.
        page.add_redact_annot(tight, fill=None)
        inserts.append((rect, new, fontsize, bold))
    _apply_text_only_redactions(page)
    for rect, text, size, is_bold in inserts:
        _insert_centered(page, rect, text, fontsize=size, bold=is_bold)


def update_designation(page: fitz.Page) -> None:
    # Cover the original 3-line offer sentence and rewrite with the longer title.
    rect = fitz.Rect(27.1, 208.5, 542.7, 255.0)
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()
    html = """
    <p style="font-family:'Noto Sans'; font-size:9.5pt; line-height:1.35; margin:0; color:#000;">
      On behalf of Altimetrik India Pvt. Limited (“Company”), we are pleased to offer you the position of
      <b>“Sr.Technical Program Manager - Program Management”</b>. Attached are the specific terms and
      conditions of our employment – please read these important details carefully, including your
      compensation and benefits.
    </p>
    """
    css = f"""
    @font-face {{
      font-family: 'Noto Sans';
      src: url({FONT_REG});
    }}
    @font-face {{
      font-family: 'Noto Sans';
      src: url({FONT_BOLD});
      font-weight: bold;
    }}
    """
    page.insert_htmlbox(rect, html, css=css)


def update_emoluments(page: fitz.Page) -> None:
    hits = page.search_for("36,00,000")
    if not hits:
        raise RuntimeError("Emoluments CTC amount not found on page 1")
    rect = hits[0]
    # Shrink vertically so redaction does not erase the following wrapped line
    # ("...we expect..."), which overlaps the full text-line bbox.
    # Keep x1 tight so the trailing "/-" after the amount is preserved.
    tight = fitz.Rect(rect.x0 - 0.3, rect.y0 + 1.0, rect.x1 - 0.2, rect.y0 + 12.5)
    page.add_redact_annot(tight, fill=(1, 1, 1))
    page.apply_redactions()
    page.insert_text(
        (rect.x0, rect.y0 + 11.0),
        "47,00,000",
        fontsize=10,
        fontfile=FONT_BOLD,
        fontname="NotoSansBold",
        color=(0, 0, 0),
    )


def update_salary_page(page: fitz.Page, salary: dict[str, tuple[int, int]]) -> None:
    """Replace Annexure I amounts in one pass so table formatting stays intact."""
    # (old_text, new_text, fontsize, bold, occurrence|None)
    replacements: list[tuple[str, str, float, bool, int | None]] = [
        ("1,08,393", inr(salary["basic"][0]), 10.5, False, None),
        ("13,00,716", inr(salary["basic"][1]), 10.0, False, None),
        ("20,507", inr(salary["lta"][0]), 10.5, False, None),
        ("2,46,084", inr(salary["lta"][1]), 10.0, False, None),
        ("65,036", inr(salary["hra"][0]), 10.5, False, None),
        ("7,80,432", inr(salary["hra"][1]), 10.0, False, None),
        ("86,011", inr(salary["conveyance"][0]), 10.5, False, None),
        ("10,32,132", inr(salary["conveyance"][1]), 10.0, False, None),
        ("2,79,947", inr(salary["fixed"][0]), 10.5, True, None),
        ("33,59,364", inr(salary["fixed"][1]), 10.0, True, None),
        ("13,007", inr(salary["pf"][0]), 10.5, False, None),
        ("1,56,084", inr(salary["pf"][1]), 10.0, False, None),
        ("7,046", inr(salary["gratuity"][0]), 10.5, False, None),
        ("84,552", inr(salary["gratuity"][1]), 10.0, False, None),
        # Gross then CTC: first/second matches in document order
        ("3,00,000", inr(salary["ctc"][0]), 10.5, True, 0),
        ("3,00,000", inr(salary["ctc"][0]), 10.5, True, 1),
        ("36,00,000", inr(salary["ctc"][1]), 10.0, True, 0),  # Gross annual
        ("36,00,000", inr(salary["ctc"][1]), 10.5, True, 1),  # CTC annual
    ]

    inserts: list[tuple[fitz.Rect, str, float, bool]] = []
    for old, new, size, bold, occurrence in replacements:
        hits = page.search_for(old)
        if not hits:
            raise RuntimeError(f"Could not find {old!r} on page {page.number + 1}")
        if occurrence is not None:
            if occurrence >= len(hits):
                raise RuntimeError(f"Missing occurrence {occurrence} of {old!r}")
            hits = [hits[occurrence]]
        for rect in hits:
            tight = fitz.Rect(rect.x0 - 0.6, rect.y0 + 0.6, rect.x1 + 0.6, rect.y1 - 0.6)
            page.add_redact_annot(tight, fill=None)
            inserts.append((rect, new, size, bold))

    _apply_text_only_redactions(page)
    for rect, text, size, is_bold in inserts:
        _insert_centered(page, rect, text, fontsize=size, bold=is_bold)


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "candidate_fad9_original.pdf")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "candidate_fad9_updated.pdf")

    salary = compute_salary()
    print("Updated salary mapping (Monthly / Annual):")
    for key, (m, a) in salary.items():
        print(f"  {key:12} {inr(m):>10}  {inr(a):>12}")

    doc = fitz.open(src)
    update_designation(doc[0])
    update_emoluments(doc[0])
    update_salary_page(doc[8], salary)
    doc.save(dst, garbage=4, deflate=True)
    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
