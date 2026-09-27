from pathlib import Path

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