import easyocr
import pymupdf


_reader = None


def get_ocr_reader():
    global _reader

    if _reader is None:
        _reader = easyocr.Reader(
            ["en"],
            gpu=False,
        )

    return _reader


def extract_pages_with_ocr(
    pdf_path: str,
) -> list[tuple[int, str]]:
    reader = get_ocr_reader()

    document = pymupdf.open(pdf_path)

    pages = []

    try:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False,
            )

            image_bytes = pixmap.tobytes("png")

            results = reader.readtext(
                image_bytes,
                detail=0,
                paragraph=True,
            )

            page_text = "\n".join(
                text.strip()
                for text in results
                if text.strip()
            )

            pages.append(
                (
                    page_number,
                    page_text,
                )
            )

    finally:
        document.close()

    return pages


def extract_text_with_ocr(
    pdf_path: str,
) -> str:
    pages = extract_pages_with_ocr(
        pdf_path
    )

    return "\n\n".join(
        text
        for _, text in pages
        if text
    ).strip()