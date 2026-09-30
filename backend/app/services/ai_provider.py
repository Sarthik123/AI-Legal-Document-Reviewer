import json
import os
import urllib.request


def call_model(messages: list[dict], max_tokens: int) -> str:
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    if provider == "cloudflare_workers_ai":
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        model = os.getenv(
            "CLOUDFLARE_AI_MODEL",
            "@cf/meta/llama-3.1-8b-instruct",
        ).strip()
        if not account_id or not token:
            raise RuntimeError("Cloudflare Workers AI is not configured.")
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
        }
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
        return str(result.get("result", {}).get("response", "")).strip()

    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
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
    return str(result["message"]["content"]).strip()
