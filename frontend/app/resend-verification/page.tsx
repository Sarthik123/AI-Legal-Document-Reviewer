"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiErrorMessage, API_URL, readApiPayload } from "../api";

export default function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/auth/verification/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await readApiPayload(response);

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not request a verification email.",
        );
      }

      setMessage(
        typeof data.message === "string"
          ? data.message
          : "If the account needs verification, an email will be sent.",
      );
    } catch (error) {
      setMessage(apiErrorMessage(error, "Could not request a verification email."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page resend-verification-page">
      <section className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-center text-sm font-semibold text-blue-600">AI Legal Document Reviewer</p>
          <h1 className="mt-3 text-center text-3xl font-bold">Resend verification</h1>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Enter your email address and we&apos;ll send a new verification link if your account needs one.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="email" className="text-sm font-medium">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Sending..." : "Send verification link"}
            </button>
          </form>

          {message && <p role="status" className="mt-5 text-center text-sm text-gray-700">{message}</p>}
          <Link href="/login" className="mt-5 block text-center text-sm text-blue-600 hover:text-blue-800">
            Back to log in
          </Link>
        </div>
      </section>
    </main>
  );
}
