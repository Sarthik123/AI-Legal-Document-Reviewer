"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Document = {
  document_id: string;
  filename: string;
  content_type: string;
  processing_status: string;
  text_length: number | null;
  created_at: string;
};

export default function DashboardPage() {
  const router = useRouter();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  async function loadDocuments() {
    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/documents",
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
        throw new Error(data.detail || "Could not load documents.");
      }

      setDocuments(data);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not load documents.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function deleteDocument(
    documentId: string,
    filename: string,
  ) {
    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    const confirmed = window.confirm(
      `Delete "${filename}"?`,
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/documents/${documentId}`,
        {
          method: "DELETE",
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
          data.detail || "Could not delete document.",
        );
      }

      setDocuments((current) =>
        current.filter(
          (document) =>
            document.document_id !== documentId,
        ),
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not delete document.",
      );
    }
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.push("/login");
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <section className="mx-auto max-w-5xl px-6 py-12">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-600">
              AI Legal Document Reviewer
            </p>

            <h1 className="mt-2 text-3xl font-bold">
              Your documents
            </h1>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => router.push("/upload")}
              className="rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
            >
              Upload document
            </button>

            <button
              onClick={handleLogout}
              className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 font-medium hover:bg-gray-50"
            >
              Log out
            </button>
          </div>
        </header>

        {message && (
          <p className="mt-6 rounded-lg bg-red-50 p-4 text-sm text-red-700">
            {message}
          </p>
        )}

        {loading ? (
          <div className="mt-10 rounded-2xl bg-white p-10 text-center shadow-sm">
            Loading documents...
          </div>
        ) : documents.length === 0 ? (
          <div className="mt-10 rounded-2xl bg-white p-10 text-center shadow-sm">
            <h2 className="text-xl font-semibold">
              No documents yet
            </h2>

            <p className="mt-2 text-gray-500">
              Upload a legal document to start your first
              review.
            </p>

            <button
              onClick={() => router.push("/upload")}
              className="mt-6 rounded-lg bg-blue-600 px-5 py-2.5 font-medium text-white hover:bg-blue-700"
            >
              Upload your first document
            </button>
          </div>
        ) : (
          <div className="mt-10 space-y-4">
            {documents.map((document) => (
              <div
                key={document.document_id}
                className="flex items-center justify-between rounded-2xl bg-white p-6 shadow-sm"
              >
                <div className="min-w-0">
                  <h2 className="truncate font-semibold">
                    {document.filename}
                  </h2>

                  <p className="mt-1 text-sm text-gray-500">
                    {document.processing_status} ·{" "}
                    {document.text_length?.toLocaleString() ?? 0}{" "}
                    characters
                  </p>

                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(
                      document.created_at,
                    ).toLocaleString()}
                  </p>
                </div>

                <div className="ml-6 flex shrink-0 gap-3">
                  <button
                    onClick={() =>
                      router.push(
                        `/documents/${document.document_id}`,
                      )
                    }
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
                  >
                    Open
                  </button>

                  <button
                    onClick={() =>
                      deleteDocument(
                        document.document_id,
                        document.filename,
                      )
                    }
                    className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}