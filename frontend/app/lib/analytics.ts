import posthog from "posthog-js";

export function initPostHog(): void {
  if (typeof window === "undefined") return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST;
  if (!key || !host) return;
  if (posthog.__loaded) return;

  posthog.init(key, {
    api_host: host,
    autocapture: false,
    capture_pageview: false,
    capture_pageleave: false,
    disable_session_recording: true,
    mask_all_element_attributes: true,
    mask_all_text: true,
    session_recording: { maskAllInputs: true },
    persistence: "localStorage+cookie",
  });
}

function getUserIdFromToken(token: string): string | null {
  try {
    const segment = token.split(".")[1];
    if (!segment) return null;
    const payload: unknown = JSON.parse(
      atob(segment.replace(/-/g, "+").replace(/_/g, "/"))
    );
    if (payload && typeof payload === "object" && "sub" in payload) {
      return String((payload as { sub: unknown }).sub);
    }
    return null;
  } catch {
    return null;
  }
}

export function identifyUser(): void {
  if (typeof window === "undefined") return;
  const token = localStorage.getItem("access_token");
  if (!token) return;
  const userId = getUserIdFromToken(token);
  if (userId) posthog.identify(userId);
}

export function resetIdentity(): void {
  posthog.reset();
}

export function trackPageView(path: string): void {
  posthog.capture("$pageview", { $current_url: path });
}

export function trackLoggedIn(): void {
  posthog.capture("logged_in");
}

export function trackUploadStarted(): void {
  posthog.capture("upload_started");
}

// Failure events carry only a short reason code and the device type: never
// error messages, file names, document text, questions, answers, or emails.
export type FailureReason = string;

export function classifyRequestError(error: unknown): FailureReason {
  if (!(error instanceof Error)) return "server_error";
  if (error.name === "AbortError") return "timeout";
  if (
    error instanceof TypeError ||
    /load failed|failed to fetch|networkerror/i.test(error.message)
  ) return "network_error";
  return "server_error";
}

// Only pass through server reason codes that look like codes (e.g. "ocr_failed").
export function safeReason(value: unknown, fallback: FailureReason): FailureReason {
  return typeof value === "string" && /^[a-z_]{1,40}$/.test(value)
    ? value
    : fallback;
}

export function deviceType(): "mobile" | "tablet" | "desktop" {
  if (typeof navigator === "undefined") return "desktop";
  const ua = navigator.userAgent;
  if (/iPad|Tablet/i.test(ua) || (/Android/i.test(ua) && !/Mobile/i.test(ua))) {
    return "tablet";
  }
  if (/Mobi|Android|iPhone|iPod/i.test(ua)) return "mobile";
  return "desktop";
}

export function trackUploadFailed(reason: FailureReason): void {
  posthog.capture("upload_failed", {
    reason,
    device_type: deviceType(),
  });
}

export function trackAnalysisFailed(reason: FailureReason): void {
  posthog.capture("analysis_failed", {
    reason,
    device_type: deviceType(),
  });
}

export function trackAnalysisCompleted(durationMs: number): void {
  posthog.capture("analysis_completed", { duration_ms: durationMs });
}

export function trackResultsViewed(): void {
  posthog.capture("results_viewed");
}

export function trackQuestionAsked(): void {
  posthog.capture("question_asked");
}
