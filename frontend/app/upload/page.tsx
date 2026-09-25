"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const router = useRouter();

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [documentId, setDocumentId] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
    }
  }, [router]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (file.type !== "application/pdf") {
      setMessage("Please select a PDF document.");
      return;
    }

    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploading(true);
    setMessage("");
    setDocumentId("");

    try {
      const response = await fetch("http://127.0.0.1:8000/documents", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        router.push("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setDocumentId(data.document_id);
      setMessage(
        `Uploaded successfully. ${data.filename} has been saved and processed.`,
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong during upload.",
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <section className="mx-auto max-w-3xl px-6 py-20">
        <div className="text-center">
          <p className="text-sm font-semibold text-blue-600">
            AI Legal Document Reviewer
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-tight">
            Review a legal document
          </h1>

          <p className="mt-4 text-gray-600">
            Upload your document to generate a plain-language summary,
            identify potential risks and missing information, and ask
            document-grounded questions.
          </p>
        </div>

        <div className="mt-10 rounded-2xl border-2 border-dashed border-gray-300 bg-white p-12 text-center">
          <div className="text-4xl">📄</div>

          <h2 className="mt-4 text-lg font-semibold">
            Upload your document
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            PDF documents supported
          </p>

          <label className="mt-6 inline-block cursor-pointer rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700">
            {uploading ? "Uploading..." : "Choose PDF"}

            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="hidden"
              disabled={uploading}
            />
          </label>

          {message && (
            <p className="mt-6 text-sm text-gray-700">
              {message}
            </p>
          )}

          {documentId && (
            <p className="mt-2 text-xs text-gray-500">
              Document ID: {documentId}
            </p>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-gray-500">
          Your document will be used only to provide document analysis.
          AI-generated information does not constitute legal advice.
        </p>
      </section>
    </main>
  );
}