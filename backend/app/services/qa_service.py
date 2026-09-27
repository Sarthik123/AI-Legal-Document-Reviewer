import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import generate_embedding


ABSTENTION_MESSAGE = (
    "The document does not provide enough information to answer this question."
)

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:3b"


@dataclass
class RetrievedSource:
    page_number: int | None
    content: str


def _normalize(text: str) -> str:
    return " ".join(
        re.sub(
            r"\s+",
            " ",
            text.lower(),
        ).split()
    )


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
        if token not in STOP_WORDS
        and len(token) > 1
    }


def is_overview_question(question: str) -> bool:
    normalized = _normalize(question)

    phrases = (
        "what is this document about",
        "what is this file about",
        "tell me about this document",
        "tell me about this file",
        "describe this document",
        "describe this file",
        "what type of document is this",
        "what kind of document is this",
        "give me an overview",
        "summarize this document",
        "summarise this document",
        "summary of this document",
    )

    return any(
        phrase in normalized
        for phrase in phrases
    )


def get_document_filename(
    db: Session,
    document_id: str,
    user_id: str,
) -> str:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        .first()
    )

    if not document:
        raise ValueError("Document not found.")

    return document.filename


def _get_document(
    db: Session,
    document_id: str,
    user_id: str,
) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        .first()
    )

    if not document:
        raise ValueError("Document not found.")

    return document


def _extract_pdf_pages(
    document: Document,
) -> list[tuple[int, str]]:
    path = Path(document.storage_path)

    if not path.exists():
        return []

    pages = []

    try:
        pdf = pymupdf.open(path)

        for index, page in enumerate(
            pdf,
            start=1,
        ):
            text = page.get_text("text").strip()

            if text:
                pages.append(
                    (
                        index,
                        text,
                    )
                )

        pdf.close()

    except Exception:
        return []

    return pages


def _page_score(
    question: str,
    page_text: str,
) -> float:
    question_tokens = _tokens(question)
    page_tokens = _tokens(page_text)

    if not question_tokens:
        return 0.0

    score = 0.0

    normalized_question = _normalize(
        question
    )

    normalized_page = _normalize(
        page_text
    )

    question_without_stop_words = " ".join(
        sorted(question_tokens)
    )

    page_without_stop_words = " ".join(
        sorted(page_tokens)
    )

    if (
        normalized_question
        and normalized_question
        in normalized_page
    ):
        score += 150.0

    if (
        len(question_tokens) >= 2
        and question_without_stop_words
        and all(
            token in page_tokens
            for token in question_tokens
        )
    ):
        score += 100.0

    overlap = len(
        question_tokens.intersection(
            page_tokens
        )
    )

    score += (
        overlap / len(question_tokens)
    ) * 100.0

    return score


def _semantic_page_fallback(
    db: Session,
    document_id: str,
    question: str,
    pages: list[tuple[int, str]],
) -> list[RetrievedSource]:
    try:
        question_embedding = generate_embedding(
            question
        )

        rows = (
            db.query(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(
                    question_embedding
                ).label("distance"),
            )
            .filter(
                DocumentChunk.document_id
                == document_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by("distance")
            .limit(8)
            .all()
        )
    except Exception:
        return []

    results = []
    seen_pages = set()

    for chunk, _distance in rows:
        chunk_start = _normalize(
            chunk.content[:250]
        )

        if not chunk_start:
            continue

        best_page = None

        for page_number, page_text in pages:
            normalized_page = _normalize(
                page_text
            )

            if chunk_start[:80] in normalized_page:
                best_page = (
                    page_number,
                    page_text,
                )
                break

        if not best_page:
            continue

        page_number, page_text = best_page

        if page_number in seen_pages:
            continue

        results.append(
            RetrievedSource(
                page_number=page_number,
                content=page_text,
            )
        )

        seen_pages.add(page_number)

        if len(results) >= 3:
            break

    return results


def retrieve_relevant_chunks(
    db: Session,
    document_id: str,
    user_id: str,
    question: str,
    top_k: int = 12,
):
    document = _get_document(
        db,
        document_id,
        user_id,
    )

    pages = _extract_pdf_pages(
        document
    )

    if pages:
        ranked_pages = []

        for page_number, page_text in pages:
            score = _page_score(
                question,
                page_text,
            )

            if score > 0:
                ranked_pages.append(
                    (
                        score,
                        page_number,
                        page_text,
                    )
                )

        ranked_pages.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        selected = []
        seen_pages = set()

        # For overview questions, keep the
        # opening pages because these usually
        # contain the title and purpose.
        if is_overview_question(
            question
        ):
            for page_number, page_text in pages[:3]:
                selected.append(
                    RetrievedSource(
                        page_number=page_number,
                        content=page_text,
                    )
                )

                seen_pages.add(
                    page_number
                )

        # Exact/lexical page matches first.
        for (
            _score,
            page_number,
            page_text,
        ) in ranked_pages:
            if page_number in seen_pages:
                continue

            selected.append(
                RetrievedSource(
                    page_number=page_number,
                    content=page_text,
                )
            )

            seen_pages.add(
                page_number
            )

            if len(selected) >= 5:
                break

        # Semantic fallback for questions
        # whose wording differs from the PDF.
        if len(selected) < 3:
            semantic_pages = (
                _semantic_page_fallback(
                    db=db,
                    document_id=document_id,
                    question=question,
                    pages=pages,
                )
            )

            for source in semantic_pages:
                if (
                    source.page_number
                    in seen_pages
                ):
                    continue

                selected.append(source)

                seen_pages.add(
                    source.page_number
                )

                if len(selected) >= 5:
                    break

        return (
            document.filename,
            selected,
        )

    # Fallback for PDFs where text extraction
    # is unavailable.
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id
            == document_id,
        )
        .order_by(
            DocumentChunk.chunk_index.asc()
        )
        .limit(top_k)
        .all()
    )

    return (
        document.filename,
        [
            RetrievedSource(
                page_number=None,
                content=chunk.content,
            )
            for chunk in chunks
        ],
    )


def _call_ollama(
    prompt: str,
) -> dict | None:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(
            payload
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=180,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    try:
        return json.loads(
            result["message"]["content"]
        )
    except (
        KeyError,
        json.JSONDecodeError,
    ):
        return None


def _best_evidence_lines(
    question: str,
    sources: list[RetrievedSource],
) -> list[str]:
    question_tokens = _tokens(
        question
    )

    candidates = []

    for source in sources:
        lines = source.content.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            text = " ".join(
                line.split()
            ).strip()

            if not text:
                continue

            line_tokens = _tokens(text)

            if not question_tokens:
                score = 0.0
            else:
                score = (
                    len(
                        question_tokens
                        & line_tokens
                    )
                    / len(question_tokens)
                ) * 100.0

            normalized_question = _normalize(
                question
            )

            normalized_line = _normalize(
                text
            )

            if (
                normalized_question
                in normalized_line
            ):
                score += 150.0

            if score <= 0:
                continue

            candidates.append(
                (
                    score,
                    source.page_number,
                    line_number,
                    text,
                )
            )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1] or 0,
            item[2],
        )
    )

    evidence = []

    for (
        _score,
        page_number,
        line_number,
        text,
    ) in candidates:
        if len(text) > 320:
            text = text[:317] + "..."

        if page_number is not None:
            evidence.append(
                f"Page {page_number} · "
                f"Line {line_number}: {text}"
            )
        else:
            evidence.append(
                f"Line {line_number}: {text}"
            )

        if len(evidence) >= 3:
            break

    return evidence


def _explicit_experience_answer(
    question: str,
    sources: list[RetrievedSource],
):
    normalized_question = _normalize(
        question
    )

    if (
        "experience"
        not in normalized_question
        and "how many years"
        not in normalized_question
    ):
        return None

    text = "\n".join(
        source.content
        for source in sources
    )

    patterns = (
        r"\b\d+(?:\.\d+)?\+?\s+years?\s+of\s+experience\b",
        r"\b\d+(?:\.\d+)?\+?\s+years?\s+experience\b",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            evidence = (
                _best_evidence_lines(
                    question,
                    sources,
                )
            )

            return (
                f"The document states "
                f"{match.group(0)}.",
                True,
                evidence,
            )

    return None


def generate_grounded_answer(
    question: str,
    filename: str,
    chunks: list,
):
    sources = chunks

    if not sources:
        return (
            ABSTENTION_MESSAGE,
            False,
            [],
        )

    experience_result = (
        _explicit_experience_answer(
            question,
            sources,
        )
    )

    if experience_result:
        return experience_result

    context_parts = []

    for source in sources[:4]:
        if source.page_number is not None:
            context_parts.append(
                f"[Page {source.page_number}]\n"
                f"{source.content}"
            )
        else:
            context_parts.append(
                f"[Document Evidence]\n"
                f"{source.content}"
            )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
You are a document-grounded assistant.

Document:
{filename}

User question:
{question}

Relevant document pages:
{context}

Rules:

1. Answer the exact question asked.
2. Use ONLY the supplied document pages.
3. Do not use outside knowledge.
4. Do not guess.
5. Understand capitalization differences.
6. Understand reasonable spelling mistakes.
7. Do not copy a heading as the answer.
8. If the user asks what something means or asks
   for details, explain it using the relevant
   sentences from the page.
9. Ignore unrelated text on the same page.
10. If the document genuinely does not contain
    enough information, say so.
11. Keep the answer concise but informative.
12. Do not invent facts.

Return ONLY JSON:

{{
  "answerable": true,
  "answer": "direct answer"
}}

OR:

{{
  "answerable": false,
  "answer": "{ABSTENTION_MESSAGE}"
}}
"""

    result = _call_ollama(
        prompt
    )

    if not result:
        return (
            ABSTENTION_MESSAGE,
            False,
            [],
        )

    if result.get(
        "answerable"
    ) is not True:
        return (
            ABSTENTION_MESSAGE,
            False,
            [],
        )

    answer = result.get(
        "answer"
    )

    if not isinstance(
        answer,
        str,
    ):
        return (
            ABSTENTION_MESSAGE,
            False,
            [],
        )

    answer = answer.strip()

    if not answer:
        return (
            ABSTENTION_MESSAGE,
            False,
            [],
        )

    evidence = _best_evidence_lines(
        question,
        sources,
    )

    if not evidence:
        # Give a page-level citation even when
        # no individual line scored strongly.
        for source in sources[:1]:
            preview = " ".join(
                source.content.split()
            ).strip()

            if len(preview) > 320:
                preview = (
                    preview[:317]
                    + "..."
                )

            if source.page_number is not None:
                evidence.append(
                    f"Page {source.page_number}: "
                    f"{preview}"
                )
            else:
                evidence.append(
                    preview
                )

    return (
        answer,
        True,
        evidence,
    )