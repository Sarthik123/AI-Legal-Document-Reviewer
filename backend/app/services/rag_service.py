from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings


def process_document_chunks(
    db: Session,
    document_id: str,
    pages: list[tuple[int, str]],
) -> int:
    chunk_index = 0
    total_chunks = 0

    pending_chunks = []
    for page_number, page_text in pages:
        if not page_text.strip():
            continue

        page_chunks = chunk_text(
            page_text
        )

        for content in page_chunks:
            pending_chunks.append((page_number, content))

    for batch_start in range(0, len(pending_chunks), 16):
        batch = pending_chunks[batch_start : batch_start + 16]
        embeddings = generate_embeddings([content for _, content in batch])

        for (page_number, content), embedding in zip(batch, embeddings):
            db.add(DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=chunk_index,
                page_number=page_number,
                content=content,
                embedding=embedding,
            ))
            chunk_index += 1
            total_chunks += 1

    db.commit()

    return total_chunks
