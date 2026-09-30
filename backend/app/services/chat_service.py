import json
import os
import re

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.qa_service import (
    generate_grounded_answer,
    get_document_filename,
    retrieve_relevant_chunks,
)
from app.services.ai_provider import call_model


ABSTENTION_MESSAGE = (
    "The document does not provide enough information to answer this question."
)


def call_ollama(prompt: str) -> str:
    return call_model([{"role": "user", "content": prompt}], 128)


def parse_json_response(response: str) -> dict | None:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None


def normalize_text(text: str) -> str:
    return " ".join(
        re.sub(
            r"[^\w\s]",
            " ",
            text.lower(),
        ).split()
    )


def meaningful_words(text: str) -> set[str]:
    stop_words = {
        "what",
        "is",
        "are",
        "was",
        "were",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "to",
        "for",
        "and",
        "or",
        "how",
        "why",
        "who",
        "when",
        "where",
        "which",
        "can",
        "do",
        "does",
        "did",
        "this",
        "that",
        "it",
        "about",
        "me",
        "tell",
        "please",
        "show",
        "give",
    }

    words = set(
        normalize_text(text).split()
    )

    return {
        word
        for word in words
        if len(word) >= 3
        and word not in stop_words
    }


def lexical_retrieve(
    db: Session,
    document_id: str,
    question: str,
    limit: int = 8,
) -> list[DocumentChunk]:
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id
            == document_id
        )
        .order_by(
            DocumentChunk.chunk_index.asc()
        )
        .all()
    )

    if not chunks:
        return []

    normalized_question = normalize_text(
        question
    )

    question_words = meaningful_words(
        question
    )

    scored_chunks = []

    for chunk in chunks:
        normalized_content = normalize_text(
            chunk.content
        )

        content_words = set(
            normalized_content.split()
        )

        score = 0

        if (
            normalized_question
            and normalized_question
            in normalized_content
        ):
            score += 100

        matching_words = (
            question_words & content_words
        )

        score += len(matching_words) * 5

        if score > 0:
            scored_chunks.append(
                (
                    score,
                    chunk.chunk_index,
                    chunk,
                )
            )

    scored_chunks.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return [
        item[2]
        for item in scored_chunks[:limit]
    ]


def merge_chunks(
    semantic_chunks: list[DocumentChunk],
    lexical_chunks: list[DocumentChunk],
    limit: int = 12,
) -> list[DocumentChunk]:
    merged = []
    seen_ids = set()

    for chunk in lexical_chunks:
        if chunk.id not in seen_ids:
            merged.append(chunk)
            seen_ids.add(chunk.id)

    for chunk in semantic_chunks:
        if chunk.id not in seen_ids:
            merged.append(chunk)
            seen_ids.add(chunk.id)

    return merged[:limit]


def is_casual_message(message: str) -> bool:
    normalized = " ".join(
        message.strip().lower().split()
    )

    return normalized in {
        "hi",
        "hello",
        "hey",
        "hey there",
        "hi there",
        "thanks",
        "thank you",
        "thx",
        "bye",
        "goodbye",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
    }


def casual_response(message: str) -> str:
    normalized = " ".join(
        message.strip().lower().split()
    )

    if normalized in {
        "bye",
        "goodbye",
        "good night",
    }:
        return "Goodbye."

    if normalized in {
        "thanks",
        "thank you",
        "thx",
    }:
        return "You're welcome."

    return (
        "Hi! Ask me anything about the document, "
        "and I'll answer using the document as the source."
    )


def classify_message(message: str) -> str:
    prompt = f"""
Classify this message for a document chatbot.

User message:
{message}

Choose exactly one category:

"document" = the user is asking about the uploaded document.

"off_topic" = the user is asking something clearly unrelated to the
uploaded document.

"casual" = simple greetings or conversational messages.

Examples:

"What is the salary?" -> document
"What company did he work at?" -> document
"What is this document about?" -> document
"What is the power of emotion in communication?" -> document
"Which month is this payslip for?" -> document
"How much experience does the person have?" -> document
"Do you believe in God?" -> off_topic
"Who is the president?" -> off_topic
"Tell me a joke" -> off_topic
"hi" -> casual
"thanks" -> casual
"bye" -> casual

Return ONLY JSON:

{{
  "category": "document"
}}
"""

    response = call_ollama(prompt)
    result = parse_json_response(response)

    if not result:
        return "document"

    category = result.get("category")

    if category in {
        "document",
        "off_topic",
        "casual",
    }:
        return category

    return "document"


def rewrite_follow_up(
    message: str,
    history: list[dict],
    filename: str,
) -> str:
    if not history:
        return message.strip()

    normalized_message = normalize_text(message)
    follow_up_starters = (
        "i mean",
        "more specifically",
        "specifically",
        "what about",
        "how about",
        "and what",
        "and how",
        "what if",
        "does that",
        "is that",
        "why is that",
        "what does that",
    )

    if not any(
        normalized_message.startswith(starter)
        for starter in follow_up_starters
    ) and len(meaningful_words(message)) > 2:
        return message.strip()

    history_text = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in history[-8:]
    )

    prompt = f"""
You are helping a document chatbot understand a follow-up question.

Document:
{filename}

Conversation:
{history_text}

Latest user message:
{message}

Rewrite ONLY the latest user message into a standalone question.

Rules:
- Preserve the user's meaning.
- Use previous conversation when necessary.
- Correct obvious spelling mistakes.
- Ignore capitalization differences.
- Do not answer the question.
- Do not add information.

Return ONLY JSON:

{{
  "question": "standalone question"
}}
"""

    try:
        response = call_ollama(prompt)
        result = parse_json_response(response)
    except Exception:
        return message.strip()

    if not result:
        return message.strip()

    rewritten = result.get("question")

    if not isinstance(rewritten, str):
        return message.strip()

    if not rewritten.strip():
        return message.strip()

    return rewritten.strip()


def chat_about_document(
    db: Session,
    document_id: str,
    user_id: str,
    message: str,
    history: list[dict],
) -> dict:

    message = message.strip()

    if not message:
        return {
            "answer": "",
            "standalone_question": "",
            "sources": [],
        }

    if is_casual_message(message):
        return {
            "answer": casual_response(message),
            "standalone_question": "",
            "sources": [],
        }

    filename = get_document_filename(
        db=db,
        document_id=document_id,
        user_id=user_id,
    )

    standalone_question = rewrite_follow_up(
        message=message,
        history=history,
        filename=filename,
    )

    _, chunks = retrieve_relevant_chunks(
    db=db,
    document_id=document_id,
    user_id=user_id,
    question=standalone_question,
    top_k=5,
)

    # Only classify as off-topic after checking the actual document.
    if not chunks:
        category = classify_message(
            standalone_question
        )

        if category == "casual":
            return {
                "answer": casual_response(
                    standalone_question
                ),
                "standalone_question": "",
                "sources": [],
            }

        if category == "off_topic":
            return {
                "answer": (
                    "I can help with questions about this "
                    "document, but that question is outside "
                    "the document."
                ),
                "standalone_question":
                    standalone_question,
                "sources": [],
            }

        return {
            "answer": ABSTENTION_MESSAGE,
            "standalone_question":
                standalone_question,
            "sources": [],
        }

    answer, supported, evidence = (
        generate_grounded_answer(
            question=standalone_question,
            filename=filename,
            chunks=chunks,
        )
    )

    return {
        "answer": answer,
        "standalone_question":
            standalone_question,
        "sources": evidence if supported else [],
    }
