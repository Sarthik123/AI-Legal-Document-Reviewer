"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { clearAccessToken } from "../auth";
import { apiErrorMessage, API_URL, readApiPayload } from "../api";
import { trackUploadFailed, trackUploadStarted } from "../lib/analytics";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const UPLOAD_TIMEOUT_MS = 180_000;
const RETRY_DELAYS_MS = [2_000, 5_000];
const FILE_READ_ERROR =
  "Couldn't open this file. Save it to your phone first, then upload.";

function isNetworkError(error: unknown): boolean {
  return (
    error instanceof TypeError ||
    (error instanceof Error &&
      /load failed|failed to fetch|networkerror/i.test(error.message))
  );
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function postWithRetry(url: string, token: string, body: FormData) {
  for (let attempt = 0; ; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

    try {
      return await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body,
        signal: controller.signal,
      });
    } catch (error) {
      // Timeouts are not retried: the server may still be processing the file.
      if (!isNetworkError(error) || attempt >= RETRY_DELAYS_MS.length) {
        throw error;
      }
      await wait(RETRY_DELAYS_MS[attempt]);
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

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

    // Android file providers (Drive, WhatsApp) sometimes report an empty type.
    const isPdf =
      file.type === "application/pdf" ||
      (!file.type && /\.pdf$/i.test(file.name));

    if (!isPdf) {
      setSelectedFile(null);
      setSuccessMessage("");
      setMessage("Please select a PDF document.");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setSelectedFile(null);
      setSuccessMessage("");
      setMessage("PDF files must be 10 MB or smaller.");

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

    setUploading(true);
    setMessage("");
    setSuccessMessage("");
    trackUploadStarted();

    // Copy the bytes into memory first. Android Chrome can lose access to
    // files picked from Drive/WhatsApp, which makes fetch fail before any
    // request is sent.
    let uploadFile: File;
    try {
      const bytes = await selectedFile.arrayBuffer();
      uploadFile = new File([bytes], selectedFile.name, {
        type: "application/pdf",
      });
    } catch (error) {
      trackUploadFailed(error, selectedFile);
      setMessage(FILE_READ_ERROR);
      setUploading(false);
      return;
    }

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const response = await postWithRetry(
        `${API_URL}/documents`,
        token,
        formData,
      );

      const data = await readApiPayload(response);

      if (response.status === 401) {
        clearAccessToken();
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Upload failed.",
        );
      }

      if (typeof data.document_id !== "string" || !data.document_id) {
        throw new Error("The server returned an invalid upload response.");
      }

      setDocumentId(data.document_id);
      setSuccessMessage("Uploaded successfully.");
    } catch (error) {
      trackUploadFailed(error, uploadFile);
      setMessage(apiErrorMessage(error, "Something went wrong during upload."));
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
              Uploading and processing document. Scanned PDFs take longer because each scanned page is read securely before analysis.
            </p>
          )}

          {message && (
            <p className="mt-4 text-red-600">
              {message}
            </p>
          )}

          <p className="mt-4 text-sm text-gray-500">
            PDF only · Maximum file size: 10 MB · No fixed page or character limit
          </p>

          <p className="mt-3 text-sm text-gray-500">
            Your documents are private to you. Delete them anytime.
          </p>
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
