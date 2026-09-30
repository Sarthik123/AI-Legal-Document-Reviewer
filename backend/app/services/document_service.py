from difflib import SequenceMatcher

import pymupdf

from pypdf import PdfReader


def extract_pages_from_pdf(
    file_path: str,
) -> list[tuple[int, str]]:
    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        pages.append(
            (
                page_number,
                text.strip(),
            )
        )

    return pages


def extract_text_from_pdf(
    file_path: str,
) -> str:
    pages = extract_pages_from_pdf(
        file_path
    )

    return "\n".join(
        text
        for _, text in pages
        if text
    ).strip()


def pages_requiring_ocr(
    file_path: str,
    extracted_pages: list[tuple[int, str]],
    minimum_native_characters: int = 50,
) -> set[int]:
    """Find scanned pages even when pypdf returns a broken OCR text layer."""
    extracted_by_page = dict(extracted_pages)
    document = pymupdf.open(file_path)
    pages = set()

    try:
        for page_number, page in enumerate(document, start=1):
            extracted_text = extracted_by_page.get(page_number, "").strip()
            native_text = (page.get_text() or "").strip()

            if (
                len(extracted_text) < minimum_native_characters
                or len(native_text) < minimum_native_characters
            ):
                pages.add(page_number)
                continue

            normalized_extracted = " ".join(extracted_text.lower().split())
            normalized_native = " ".join(native_text.lower().split())
            similarity = SequenceMatcher(
                None,
                normalized_extracted,
                normalized_native,
                autojunk=False,
            ).ratio()

            if similarity < 0.55:
                pages.add(page_number)
    finally:
        document.close()

    return pages
