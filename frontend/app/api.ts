export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://api.lawyerlens.in"
    : "http://127.0.0.1:8000");

export type ApiPayload = Record<string, unknown>;

export async function readApiPayload(
  response: Response,
): Promise<ApiPayload> {
  const body = await response.text();

  if (!body) {
    return {};
  }

  try {
    const parsed: unknown = JSON.parse(body);

    if (parsed && typeof parsed === "object") {
      return parsed as ApiPayload;
    }
  } catch {
    // Some proxy/server failures return plain text instead of JSON.
  }

  return {};
}

export function apiErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (!(error instanceof Error) || !error.message.trim()) {
    return fallback;
  }

  if (error.name === "AbortError") {
    return "Upload timed out. Try on Wi-Fi or a faster connection, then retry.";
  }

  if (/load failed|failed to fetch|networkerror/i.test(error.message)) {
    return "Could not reach the server. Check your connection or try on Wi-Fi.";
  }

  return error.message;
}
