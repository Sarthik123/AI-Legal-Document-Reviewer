import os
import json
import urllib.request

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

_model = None


def _cloudflare_embedding(text: str) -> list[float]:
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    model = os.getenv(
        "CLOUDFLARE_EMBEDDING_MODEL",
        "@cf/baai/bge-small-en-v1.5",
    ).strip()

    if not account_id or not token:
        raise RuntimeError("Cloudflare Workers AI is not configured for embeddings.")

    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}",
        data=json.dumps({"text": [text]}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload.get("success"):
        raise RuntimeError("Cloudflare Workers AI embedding request failed.")

    vectors = payload.get("result", {}).get("data")
    if not isinstance(vectors, list) or not vectors or not isinstance(vectors[0], list):
        raise RuntimeError("Cloudflare Workers AI returned an invalid embedding.")

    embedding = vectors[0]
    if len(embedding) != 384:
        raise RuntimeError(
            f"Embedding dimension {len(embedding)} does not match vector(384)."
        )
    return [float(value) for value in embedding]


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
        try:
            import torch

            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except (ImportError, RuntimeError):
            pass
    return _model


def release_embedding_model() -> None:
    global _model
    if _model is None:
        return
    _model = None
    try:
        import gc
        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except (ImportError, RuntimeError):
        pass


def generate_embedding(text: str) -> list[float]:
    if os.getenv("AI_PROVIDER", "ollama").strip().lower() == "cloudflare_workers_ai":
        return _cloudflare_embedding(text)

    embedding = get_embedding_model().encode(text)
    return embedding.tolist()
