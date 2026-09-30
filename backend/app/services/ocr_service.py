import gc

import pymupdf


_reader = None


def get_ocr_reader():
    global _reader

    if _reader is None:
        from app.services.embedding_service import release_embedding_model

        release_embedding_model()
        import easyocr

        _reader = easyocr.Reader(
            ["en"],
            gpu=False,
        )

    return _reader


def extract_pages_with_ocr(
    pdf_path: str,
    page_numbers: set[int] | None = None,
) -> list[tuple[int, str]]:
    reader = get_ocr_reader()

    document = pymupdf.open(pdf_path)

    pages = []

    try:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            if page_numbers is not None and page_number not in page_numbers:
                continue

            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(3, 3),
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
        # OCR is only needed while processing scanned pages. Release its
        # reader before embeddings are loaded so a 512 MB instance does not
        # retain both ML models.
        global _reader
        _reader = None
        gc.collect()

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
