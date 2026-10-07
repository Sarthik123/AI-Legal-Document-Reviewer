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

type UploadErrorType = "network_error" | "timeout" | "server_error";

function classifyUploadError(error: unknown): UploadErrorType {
  if (!(error instanceof Error)) return "server_error";
  if (error.name === "AbortError") return "timeout";
  const msg = error.message.toLowerCase();
  if (
    msg.includes("unable to reach") ||
    msg.includes("could not reach") ||
    msg.includes("network") ||
    msg.includes("load failed") ||
    msg.includes("failed to fetch")
  ) return "network_error";
  if (msg.includes("timed out") || msg.includes("timeout")) return "timeout";
  return "server_error";
}

export function trackUploadFailed(error: unknown): void {
  posthog.capture("upload_failed", { error_type: classifyUploadError(error) });
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
