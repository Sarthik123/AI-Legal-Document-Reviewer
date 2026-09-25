"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

type Document = {
  document_id: string;
  filename: string;
  content_type: string;
  processing_status: string;
  text_length: number | null;
  created_at: string;
};

export default function DocumentPage() {
  const router = useRouter();
  const params = useParams();

  const documentId = params.id as string;

  const [document, setDocument] =
    useState<Document | null>(null);

  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadDocument() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/documents/${documentId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        if (response.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Could not load document.",
          );
        }

        setDocument(data);
      } catch (error) {
        setMessage(
          error instanceof Error
            ? error.message
            : "Could not load document.",
        );
      } finally {
        setLoading(false);
      }
    }

    loadDocument();
  }, [documentId, router]);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 p-10 text-center">
        Loading document...
      </main>
    );
  }

  if (!document) {
    return (
      <main className="min-h-screen bg-gray-50 px-6 py-12">
        <div className="mx-auto max-w-3xl rounded-2xl bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold">
            Document unavailable
          </h1>

          <p className="mt-3 text-red-600">
            {message}
          </p>

          <button
            onClick={() => router.push("/dashboard")}
            className="mt-6 rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white"
          >
            Back to dashboard
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <section className="mx-auto max-w-4xl px-6 py-12">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          ← Back to dashboard
        </button>

        <div className="mt-8 rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-sm font-semibold text-blue-600">
            Document
          </p>

          <h1 className="mt-2 text-3xl font-bold">
            {document.filename}
          </h1>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-sm text-gray-500">
                Status
              </p>

              <p className="mt-1 font-medium">
                {document.processing_status}
              </p>
            </div>

            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-sm text-gray-500">
                Text extracted
              </p>

              <p className="mt-1 font-medium">
                {document.text_length?.toLocaleString() ?? 0}{" "}
                characters
              </p>
            </div>

            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-sm text-gray-500">
                File type
              </p>

              <p className="mt-1 font-medium">
                {document.content_type}
              </p>
            </div>

            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-sm text-gray-500">
                Uploaded
              </p>

              <p className="mt-1 font-medium">
                {new Date(
                  document.created_at,
                ).toLocaleString()}
              </p>
            </div>
          </div>

          <div className="mt-10 rounded-xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="font-semibold">
              AI review coming next
            </h2>

            <p className="mt-2 text-sm text-gray-600">
              The document has been uploaded and processed.
              The next implementation step will extract,
              chunk, embed, and retrieve document content so
              the AI can generate summaries, risks, citations,
              and grounded answers.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}