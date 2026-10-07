import json
import os
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

import app.posthog as posthog_integration


_ai_observability_context: ContextVar[dict | None] = ContextVar(
    "ai_observability_context",
    default=None,
)


@contextmanager
def ai_observability_context(session_id: str, distinct_id: str):
    """Group the model calls in one user turn into a PostHog AI trace."""
    token = _ai_observability_context.set(
        {
            "session_id": session_id,
            "trace_id": str(uuid4()),
            "distinct_id": distinct_id,
        }
    )
    try:
        yield
    finally:
        _ai_observability_context.reset(token)


def _capture_generation(
    messages: list[dict],
    max_tokens: int,
    provider: str,
    model: str,
    latency: float,
    output: str | None = None,
    error: Exception | None = None,
) -> None:
    """Capture a raw provider call when it belongs to an instrumented turn."""
    context = _ai_observability_context.get()
    client = posthog_integration.posthog_client
    if context is None or client is None:
        return

    properties = {
        "$ai_trace_id": context["trace_id"],
        "$ai_session_id": context["session_id"],
        "$ai_model": model,
        "$ai_provider": provider,
        "$ai_latency": latency,
        "$ai_stream": False,
        "$ai_temperature": 0,
        "$ai_max_tokens": max_tokens,
    }
    if error is not None:
        properties["$ai_is_error"] = True
        properties["$ai_error"] = type(error).__name__

    client.capture(
        "$ai_generation",
        distinct_id=context["distinct_id"],
        properties=properties,
    )


def call_model(
    messages: list[dict],
    max_tokens: int,
    response_format: dict | None = None,
) -> str:
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    is_cloudflare = provider == "cloudflare_workers_ai"
    ai_provider = "cloudflare" if is_cloudflare else "ollama"
    model = os.getenv(
        "CLOUDFLARE_AI_MODEL",
        "@cf/meta/llama-3.1-8b-instruct",
    ).strip() if is_cloudflare else os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    started_at = perf_counter()

    try:
        if is_cloudflare:
            account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
            token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
            if not account_id or not token:
                raise RuntimeError("Cloudflare Workers AI is not configured.")
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0,
            }
            if response_format:
                payload["response_format"] = response_format
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not result.get("success"):
                raise RuntimeError("Cloudflare Workers AI request failed.")
            content = result.get("result", {}).get("response", "")
            # JSON Mode can return the response as an object. Serializing it here
            # keeps the provider interface consistent for callers that parse JSON.
            output = json.dumps(content) if isinstance(content, (dict, list)) else str(content).strip()
        else:
            url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
            request = urllib.request.Request(
                url,
                data=json.dumps({
                    "model": model,
                    "keep_alive": "15m",
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": 8192},
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
            output = str(result["message"]["content"]).strip()
    except Exception as error:
        _capture_generation(
            messages,
            max_tokens,
            ai_provider,
            model,
            perf_counter() - started_at,
            error=error,
        )
        raise

    _capture_generation(
        messages,
        max_tokens,
        ai_provider,
        model,
        perf_counter() - started_at,
        output=output,
    )
    return output
