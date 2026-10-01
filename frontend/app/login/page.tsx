"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { storeAccessToken } from "../auth";
import { apiErrorMessage, API_URL, readApiPayload } from "../api";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setMessage("");

    try {
      const formData = new URLSearchParams();

      formData.append("username", email);
      formData.append("password", password);

      const response = await fetch(
        `${API_URL}/auth/token`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData.toString(),
        },
      );

      const data = await readApiPayload(response);

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Login failed.",
        );
      }

      if (typeof data.access_token !== "string" || !data.access_token) {
        throw new Error("The server returned an invalid login response.");
      }

      storeAccessToken(data.access_token);

      router.push("/upload");
    } catch (error) {
      setMessage(
        apiErrorMessage(error, "Login failed."),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page login-page">
      <section className="mx-auto max-w-md px-6 py-20">
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-center text-sm font-semibold text-blue-600">
            AI Legal Document Reviewer
          </p>

          <h1 className="mt-3 text-center text-3xl font-bold">
            Log in
          </h1>

          <form onSubmit={handleLogin} className="mt-8 space-y-5">
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
                className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Logging in..." : "Log in"}
            </button>
          </form>

          <div className="mt-4 flex justify-between text-sm">
            <Link href="/forgot-password" className="text-blue-600 hover:text-blue-800">
              Forgot password?
            </Link>
            <Link href="/resend-verification" className="text-blue-600 hover:text-blue-800">
              Resend verification
            </Link>
          </div>

          <button
            type="button"
            onClick={() => router.push("/register")}
            className="mt-4 w-full text-center text-sm text-gray-600 hover:text-black"
          >
            Create an account
          </button>

          {message && (
            <p className="mt-5 text-center text-sm text-red-600">
              {message}
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
