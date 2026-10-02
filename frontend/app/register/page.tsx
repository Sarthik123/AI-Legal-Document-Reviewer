"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiErrorMessage, apiFetch, API_URL, readApiPayload } from "../api";

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [registrationSucceeded, setRegistrationSucceeded] = useState(false);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setMessage("");
    setRegistrationSucceeded(false);
    setVerificationRequired(false);

    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setMessage("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await apiFetch(
        `${API_URL}/auth/register`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
          }),
        },
      );

      const data = await readApiPayload(response);

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Registration failed.",
        );
      }

      setRegistrationSucceeded(true);
      setVerificationRequired(data.verification_required === true);
      setMessage(
        typeof data.message === "string" ? data.message : "Account created.",
      );
    } catch (error) {
      setMessage(apiErrorMessage(error, "Registration failed."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page register-page">
      <section className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-center text-sm font-semibold text-blue-600">
            AI Legal Document Reviewer
          </p>

          <h1 className="mt-3 text-center text-3xl font-bold">
            Create an account
          </h1>

          <form onSubmit={handleRegister} className="mt-8 space-y-5">
            <div>
              <label className="text-sm font-medium">
                Email
              </label>

              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-sm font-medium">
                Password
              </label>

              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-sm font-medium">
                Confirm Password
              </label>

              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          {message && (
            <p className={`mt-5 text-center text-sm ${registrationSucceeded ? "text-green-700" : "text-red-600"}`}>
              {message}
            </p>
          )}

          {registrationSucceeded && verificationRequired && (
            <button
              type="button"
              onClick={() => router.push("/resend-verification")}
              className="mt-3 w-full text-center text-sm text-blue-600 hover:text-blue-800"
            >
              Didn&apos;t receive the email? Resend verification
            </button>
          )}

          <button
            type="button"
            onClick={() => router.push("/login")}
            className="mt-4 w-full text-center text-sm text-gray-600 hover:text-black"
          >
            Already have an account? Log in
          </button>
        </div>
      </section>
    </main>
  );
}
