"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_URL } from "../api";

export default function VerifyEmailPage() {
  const [message, setMessage] = useState("Verifying your email...");

  useEffect(() => {
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
          const data = await response.json();
          throw new Error(data.detail || "Could not verify this email address.");
        }

        const data = await response.json();
        setMessage(data.message);
      })
      .catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : "Could not verify this email address.");
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
