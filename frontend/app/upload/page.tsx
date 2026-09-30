"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { clearAccessToken } from "../auth";
import { API_URL } from "../api";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
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
      setSuccessMessage("");
      setMessage("Please select a PDF document.");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      return;
    }

    setSelectedFile(file);
    setMessage("");
    setSuccessMessage("");
    setDocumentId("");
  }

  function handleRemoveFile() {
    setSelectedFile(null);
    setDocumentId("");
    setSuccessMessage("");
    setMessage("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleUpload() {
    if (!selectedFile || documentId) {
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
    setSuccessMessage("");

    try {
      const response = await fetch(
        `${API_URL}/documents`,
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
        clearAccessToken();
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setDocumentId(data.document_id);
      setSuccessMessage("Uploaded successfully.");
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
    <main className="app-page upload-page">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-bold">
          Review a Document
        </h1>

        <p className="mt-3 text-gray-600">
          Upload a PDF to begin your legal document review.
        </p>

        <div className="mt-8 rounded-xl border border-gray-200 p-6">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            disabled={uploading || Boolean(selectedFile)}
            className="block w-full"
          />

          {selectedFile && (
            <div className="mt-4 flex items-center gap-3">
              <p className="min-w-0 truncate text-sm text-gray-700">
                Selected: {selectedFile.name}
              </p>

              <button
                type="button"
                onClick={handleRemoveFile}
                disabled={uploading}
                aria-label="Remove selected file"
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-gray-300 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              >
                ×
              </button>
            </div>
          )}

          {selectedFile && (
            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading || Boolean(documentId)}
              className="mt-4 rounded-lg bg-black px-5 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading
                ? "Uploading..."
                : documentId
                  ? "Uploaded"
                  : "Upload Document"}
            </button>
          )}

          {uploading && (
            <p className="upload-progress mt-4 text-gray-600">
              Uploading and processing document...
            </p>
          )}

          {message && (
            <p className="mt-4 text-red-600">
              {message}
            </p>
          )}
        </div>

        {(successMessage || documentId) && (
          <div className="mt-4 flex items-center justify-between gap-4">
            {successMessage && (
              <p className="text-sm text-gray-700">
                {successMessage}
              </p>
            )}

            {documentId && (
              <button
                type="button"
                onClick={() => router.push("/dashboard")}
                className="rounded-lg bg-black px-5 py-2 text-white"
              >
                Go to Dashboard
              </button>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
