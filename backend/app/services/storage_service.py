from pathlib import Path
from uuid import uuid4


STORAGE_DIR = Path("storage/documents")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_document(filename: str, file_data: bytes) -> tuple[str, str]:
    document_id = str(uuid4())
    safe_filename = Path(filename).name
    stored_filename = f"{document_id}_{safe_filename}"

    file_path = STORAGE_DIR / stored_filename
    file_path.write_bytes(file_data)

    return document_id, str(file_path)