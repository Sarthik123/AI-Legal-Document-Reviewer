"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function UploadPage() {
  const router = useRouter();

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (file.type !== "application/pdf") {
      setSelectedFile(null);
      setMessage("Please select a PDF document.");
      return;
    }

    setSelectedFile(file);
    setMessage("");
    setDocumentId("");
  }

  async function handleUpload() {
    if (!selectedFile) {
      setMessage("Please select a PDF document first.");
      return;
    }

    const token = localStorage.getItem("access_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setUploading(true);
    setMessage("");
    setDocumentId("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/documents",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      const data = await response.json();

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setDocumentId(data.document_id);
      setMessage(
        `Uploaded successfully. ${data.filename} has been processed.`
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong during upload."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white px-6 py-16 text-gray-900">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-bold">
          Review a Document
        </h1>

        <p className="mt-3 text-gray-600">
          Upload a PDF to begin your legal document review.
        </p>

        <div className="mt-8 rounded-xl border border-gray-200 p-6">
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            disabled={uploading}
            className="block w-full"
          />

          {selectedFile && (
            <div className="mt-4">
              <p className="text-sm text-gray-700">
                Selected: {selectedFile.name}
              </p>

              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading}
                className="mt-4 rounded-lg bg-black px-5 py-2 text-white disabled:opacity-50"
              >
                {uploading ? "Uploading..." : "Upload Document"}
              </button>
            </div>
          )}

          {uploading && (
            <p className="mt-4 text-gray-600">
              Uploading and processing document...
            </p>
          )}

          {message && (
            <p className="mt-4 text-gray-700">
              {message}
            </p>
          )}

          {documentId && (
            <button
              type="button"
              onClick={() => router.push("/dashboard")}
              className="mt-4 rounded-lg bg-black px-5 py-2 text-white"
            >
              Go to Dashboard
            </button>
          )}
        </div>

        <p className="mt-8 text-sm text-gray-500">
          This tool provides AI-assisted document analysis and is not a
          substitute for professional legal advice.
        </p>
      </div>
    </main>
  );
}