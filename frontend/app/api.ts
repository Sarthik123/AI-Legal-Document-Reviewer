export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://api.lawyerlens.in"
    : "http://127.0.0.1:8000");

const REQUEST_TIMEOUT_MS = 45_000;
const MAX_RETRIES = 2;

type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
  retries?: number;
};

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function isRetryableStatus(status: number): boolean {
  return [408, 425, 429, 500, 502, 503, 504].includes(status);
}

/** Fetch API requests with bounded timeouts and transient-failure retries. */
export async function apiFetch(
  input: RequestInfo | URL,
  options: ApiFetchOptions = {},
): Promise<Response> {
  const { timeoutMs = REQUEST_TIMEOUT_MS, retries = MAX_RETRIES, ...init } = options;
  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    const externalSignal = init.signal;
    const abortExternal = () => controller.abort();

    externalSignal?.addEventListener("abort", abortExternal, { once: true });

    try {
      const response = await fetch(input, {
        ...init,
        signal: controller.signal,
      });

      if (!isRetryableStatus(response.status) || attempt === retries) {
        return response;
      }

      lastError = new Error(`Temporary server error (${response.status}).`);
    } catch (error) {
      lastError = error;

      if (externalSignal?.aborted) {
        throw error;
      }
    } finally {
      window.clearTimeout(timeout);
      externalSignal?.removeEventListener("abort", abortExternal);
    }

    await wait(500 * 2 ** attempt);
  }

  if (lastError instanceof DOMException && lastError.name === "AbortError") {
    throw new Error("The server took too long to respond. Please try again.");
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("Unable to reach the server. Please try again.");
}

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

  if (/load failed|failed to fetch|networkerror/i.test(error.message)) {
    return "Unable to reach the server. Please try again.";
  }

  return error.message;
}
