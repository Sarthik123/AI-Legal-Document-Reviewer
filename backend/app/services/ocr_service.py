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


def extract_text_with_ocr(pdf_path: str) -> str:
    reader = get_ocr_reader()

    document = pymupdf.open(pdf_path)
    pages = []

    try:
        for page in document:
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

            if page_text:
                pages.append(page_text)

    finally:
        document.close()

    return "\n\n".join(pages).strip()