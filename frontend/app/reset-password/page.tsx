"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { API_URL } from "../api";

const PASSWORD_RESET_ENABLED = process.env.NEXT_PUBLIC_PASSWORD_RESET_ENABLED === "true";

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [complete, setComplete] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setComplete(false);

    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    const token = new URLSearchParams(window.location.search).get("token");

    if (!token) {
      setMessage("The password reset link is missing its token.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/auth/password-reset/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not reset your password.");
      }

      setComplete(true);
      setMessage(data.message);
      setPassword("");
      setConfirmPassword("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not reset your password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page reset-password-page">
      <section className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-center text-sm font-semibold text-blue-600">AI Legal Document Reviewer</p>
          <h1 className="mt-3 text-center text-3xl font-bold">Reset password</h1>

          {PASSWORD_RESET_ENABLED && !complete && (
            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div>
                <label htmlFor="password" className="text-sm font-medium">New password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={8}
                  maxLength={128}
                  required
                  className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label htmlFor="confirm-password" className="text-sm font-medium">Confirm new password</label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={8}
                  maxLength={128}
                  required
                  className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "Updating..." : "Update password"}
              </button>
            </form>
          )}

          {!PASSWORD_RESET_ENABLED && (
            <p role="status" className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
              Password reset is temporarily unavailable. Please try again later.
            </p>
          )}

          {message && <p role="status" className="mt-5 text-center text-sm text-gray-700">{message}</p>}
          <Link href="/login" className="mt-5 block text-center text-sm text-blue-600 hover:text-blue-800">
            Back to log in
          </Link>
        </div>
      </section>
    </main>
  );
}
