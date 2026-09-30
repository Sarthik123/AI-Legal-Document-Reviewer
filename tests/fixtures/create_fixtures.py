from pathlib import Path

import pymupdf


OUTPUT = Path(__file__).parent

AGREEMENT_LINES = [
    "NORTHSTAR SERVICE AGREEMENT",
    "Synthetic E2E fixture; no real parties or obligations.",
    "Customer: Northstar Bicycle LLC.",
    "Provider: Blue Mesa Design LLC.",
    "Effective date: July 1, 2026.",
    "Services: Provider will deliver two monthly product-design reports.",
    "Customer must pay Provider $4,250 per month, due on the first day of each month.",
    "The initial term is 12 months, starting July 1, 2026.",
    "Provider may terminate this agreement at any time without notice. Customer cannot terminate during the initial term.",
    "Provider's total liability for any claim is capped at $10, regardless of the loss.",
    "Customer must cover all claims, including claims caused by Provider's own negligence, with no cap.",
    "This agreement does not name a governing law or dispute-resolution forum.",
]

SCANNED_LINES = [
    "OCR SERVICE AGREEMENT",
    "Synthetic image-only document for local OCR verification.",
    "Customer: Meadow Test Company.",
    "OCR verification token: PINEAPPLE-7391-OTTER.",
    "Monthly amount: $1,275.",
    "This fixture contains no real personal or legal information.",
]


def render_lines(page: pymupdf.Page, lines: list[str], font_size: int = 11) -> None:
    y = 64
    for line in lines:
        page.insert_text((54, y), line, fontname="helv", fontsize=font_size)
        y += 38


def make_digital_pdf() -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    render_lines(page, AGREEMENT_LINES)
    document.set_metadata({"title": "Synthetic E2E Service Agreement"})
    document.save(OUTPUT / "synthetic-service-agreement.pdf")
    document.close()


def make_scanned_pdf() -> None:
    source = pymupdf.open()
    page = source.new_page(width=595, height=842)
    render_lines(page, SCANNED_LINES, font_size=15)
    image = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes(
        "jpeg",
        jpg_quality=85,
    )
    source.close()

    scanned = pymupdf.open()
    page = scanned.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=image)
    scanned.set_metadata({"title": "Synthetic OCR E2E Agreement"})
    scanned.save(OUTPUT / "synthetic-scanned-agreement.pdf")
    scanned.close()


if __name__ == "__main__":
    make_digital_pdf()
    make_scanned_pdf()
