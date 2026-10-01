"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { apiErrorMessage, API_URL, readApiPayload } from "../api";

export default function VerifyEmailPage() {
  const [message, setMessage] = useState("Verifying your email...");
  const verificationStarted = useRef(false);

  useEffect(() => {
    // React Strict Mode runs effects twice during local development. Email
    // verification tokens are single-use, so prevent a duplicate request.
    if (verificationStarted.current) return;
    verificationStarted.current = true;

    const token = new URLSearchParams(window.location.search).get("token");

    Promise.resolve()
      .then(() => {
        if (!token) {
          throw new Error("The verification link is missing its token.");
        }

        return fetch(`${API_URL}/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
      })
      .then(async (response) => {
        if (!response.ok) {
          const data = await readApiPayload(response);
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "Could not verify this email address.",
          );
        }

        const data = await readApiPayload(response);
        setMessage(
          typeof data.message === "string"
            ? data.message
            : "Email verified. You can now log in.",
        );
      })
      .catch((error: unknown) => {
        setMessage(apiErrorMessage(error, "Could not verify this email address."));
      });
  }, []);

  return (
    <main className="auth-page verify-email-page">
      <section className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-semibold text-blue-600">AI Legal Document Reviewer</p>
          <h1 className="mt-3 text-3xl font-bold">Email verification</h1>
          <p role="status" className="mt-5 text-sm leading-6 text-gray-700">{message}</p>
          <Link href="/login" className="mt-6 inline-block text-sm text-blue-600 hover:text-blue-800">
            Continue to log in
          </Link>
        </div>
      </section>
    </main>
  );
}
