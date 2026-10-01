"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { clearAccessToken } from "../../auth";
import {
  apiErrorMessage,
  API_URL,
  readApiPayload,
} from "../../api";

type DocumentData = {
  document_id: string;
  filename: string;
  content_type: string;
  processing_status: string;
  text_length: number | null;
  created_at: string;
};

type ChatSource = {
  source: number;
  content: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
};

type DocumentAnalysis = {
  summary: string;
  key_points: string[];
  risks: {
    title: string;
    severity: "high" | "medium" | "low";
    description: string;
    source: number;
    evidence: string;
  }[];
  missing_information: {
    item: string;
    description: string;
    source: number;
    evidence: string;
  }[];
};

export default function DocumentPage() {
  const params = useParams();
  const router = useRouter();

  const documentId = params.id as string;

  const [document, setDocument] = useState<DocumentData | null>(null);
  const [pdfUrl, setPdfUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState("");

  const [analysis, setAnalysis] =
    useState<DocumentAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] =
    useState(false);
  const [analysisError, setAnalysisError] =
    useState("");

  const chatContainerRef =
    useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    async function runAnalysis() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        return;
      }

      setAnalysisLoading(true);
      setAnalysisError("");

      try {
        const response = await fetch(
          `${API_URL}/documents/${documentId}/analyze`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = await readApiPayload(response);

        if (!response.ok) {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "Failed to analyze document."
          );
        }

        setAnalysis(data as unknown as DocumentAnalysis);
      } catch (error) {
        setAnalysisError(apiErrorMessage(error, "Failed to analyze document."));
      } finally {
        setAnalysisLoading(false);
      }
    }

    runAnalysis();
  }, [documentId]);

  useEffect(() => {
    let objectUrl = "";

    async function loadDocument() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const documentResponse = await fetch(
        `${API_URL}/documents/${documentId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const documentData = await readApiPayload(documentResponse);

        if (documentResponse.status === 401) {
          clearAccessToken();
          router.replace("/login");
          return;
        }

        if (!documentResponse.ok) {
          throw new Error(
            typeof documentData.detail === "string"
              ? documentData.detail
              :
              "Failed to load document."
          );
        }

        setDocument(documentData as unknown as DocumentData);

        const pdfResponse = await fetch(
        `${API_URL}/documents/${documentId}/file`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!pdfResponse.ok) {
          const pdfError = await readApiPayload(pdfResponse);

          throw new Error(
            typeof pdfError.detail === "string"
              ? pdfError.detail
              :
              "Failed to load PDF."
          );
        }

        const pdfBlob = await pdfResponse.blob();

        objectUrl =
          URL.createObjectURL(pdfBlob);

        setPdfUrl(objectUrl);
      } catch (error) {
        setMessage(apiErrorMessage(error, "Failed to load document."));
      } finally {
        setLoading(false);
      }
    }

    loadDocument();

    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [documentId, router]);

  useEffect(() => {
    async function loadChatHistory() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        return;
      }

      try {
        const response = await fetch(
          `${API_URL}/documents/${documentId}/chat`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.status === 401) {
          clearAccessToken();
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          return;
        }

        const data = await readApiPayload(response);

        setChatMessages(
  (Array.isArray(data.messages) ? data.messages : []).map(
    (message: ChatMessage) => ({
      role: message.role,
      content: message.content,
      sources: message.sources || [],
    })
  )
);
      } catch {
        // Keep the chat usable if history loading fails.
      }
    }

    loadChatHistory();
  }, [documentId, router]);

  useEffect(() => {
    const container =
      chatContainerRef.current;

    if (!container) {
      return;
    }

    container.scrollTop =
      container.scrollHeight;
  }, [chatMessages, chatSending]);

  async function handleChatSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const trimmedMessage =
      chatInput.trim();

    if (!trimmedMessage || chatSending) {
      return;
    }

    const token =
      localStorage.getItem("access_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    const previousHistory =
      chatMessages.map((item) => ({
        role: item.role,
        content: item.content,
      }));

    const userMessage: ChatMessage = {
      role: "user",
      content: trimmedMessage,
    };

    setChatMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setChatInput("");
    setChatError("");
    setChatSending(true);

    try {
      const response = await fetch(
        `${API_URL}/documents/${documentId}/chat`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: trimmedMessage,
            history: previousHistory,
          }),
        }
      );

      const data = await readApiPayload(response);

      if (response.status === 401) {
        clearAccessToken();
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            :
            "Failed to get a response."
        );
      }

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content:
          typeof data.answer === "string"
            ? data.answer
            : "The server returned an empty response.",
        sources: Array.isArray(data.sources) ? data.sources as ChatSource[] : [],
      };

      setChatMessages((previous) => [
        ...previous,
        assistantMessage,
      ]);
    } catch (error) {
      setChatError(apiErrorMessage(error, "Failed to get a response."));
    } finally {
      setChatSending(false);
    }
  }

  async function clearChat() {
    const token =
      localStorage.getItem("access_token");

    if (!token) {
      router.replace("/login");
      return;
    }

    try {
      setChatError("");

      const response = await fetch(
        `${API_URL}/documents/${documentId}/chat`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await readApiPayload(response);

      if (response.status === 401) {
        clearAccessToken();
        router.replace("/login");
        return;
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Failed to clear chat."
        );
      }

      setChatMessages([]);
      setChatInput("");
    } catch (error) {
      setChatError(apiErrorMessage(error, "Failed to clear chat."));
    }
  }

  if (loading) {
    return (
      <main className="app-page document-page">
        <div className="mx-auto max-w-6xl">
          <p className="document-loading">Loading document...</p>
        </div>
      </main>
    );
  }

  if (message || !document) {
    return (
      <main className="app-page document-page">
        <div className="mx-auto max-w-6xl">
          <p className="document-load-error text-red-600">
            {message || "Document not found."}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="app-page document-page">
      <div className="mx-auto max-w-7xl">
        <button
          type="button"
          onClick={() =>
            router.push("/dashboard")
          }
          className="mb-6 text-sm text-gray-600 hover:text-black"
        >
          ← Back to Dashboard
        </button>

        <h1 className="text-3xl font-bold">
          {document.filename}
        </h1>

        <p className="mt-2 text-gray-600">
          Document Review
        </p>

        <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-5 py-3">
            <h2 className="font-semibold">
              PDF Document
            </h2>
          </div>

          {pdfUrl ? (
            <iframe
              src={pdfUrl}
              title={document.filename}
              className="h-[800px] w-full"
            />
          ) : (
            <div className="p-6">
              <p>
                Unable to display the PDF.
              </p>
            </div>
          )}
        </div>

        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-xl font-semibold">
            Document Information
          </h2>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-gray-500">
                Status
              </p>

              <p className="mt-1 font-medium">
                {document.processing_status}
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-500">
                File Type
              </p>

              <p className="mt-1 font-medium">
                {document.content_type}
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-500">
                Text Extracted
              </p>

              <p className="mt-1 font-medium">
                {document.text_length ?? 0} characters
              </p>
            </div>

            <div>
              <p className="text-sm text-gray-500">
                Uploaded
              </p>

              <p className="mt-1 font-medium">
                {new Date(
                  document.created_at
                ).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-xl font-semibold">
            AI Analysis
          </h2>

          {analysisLoading && (
            <p className="analysis-skeleton mt-4 text-sm text-gray-500">
              Analyzing document...
            </p>
          )}

          {analysisError && !analysisLoading && (
            <div className="analysis-error mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-700">
                {analysisError}
              </p>
            </div>
          )}

          {analysis && !analysisLoading && (
            <div className="mt-5 space-y-6">
              <div>
                <h3 className="font-semibold">
                  Summary
                </h3>

                <p className="mt-2 text-sm leading-6 text-gray-700">
                  {analysis.summary}
                </p>
              </div>

              {analysis.key_points.length > 0 && (
                <div>
                  <h3 className="font-semibold">
                    Key Points
                  </h3>

                  <div className="mt-2 space-y-2">
                    {analysis.key_points.map(
                      (point, index) => (
                        <div
                          key={index}
                          className="rounded-lg border border-gray-200 p-3 text-sm text-gray-700"
                        >
                          {point}
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              <div>
                <h3 className="font-semibold">
                  Potential Risks
                </h3>

                {analysis.risks.length === 0 ? (
                  <p className="mt-2 text-sm text-gray-500">
                    No potential risks were identified.
                  </p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {analysis.risks.map(
                      (risk, index) => (
                        <details
                          key={index}
                          className="rounded-lg border border-gray-200 p-4"
                        >
                          <summary className="cursor-pointer font-medium">
                            {risk.title} —{" "}
                            {risk.severity}
                          </summary>

                          <p className="mt-3 text-sm text-gray-700">
                            {risk.description}
                          </p>

                          {risk.evidence && (
                            <div className="mt-3 rounded-lg bg-gray-50 p-3">
                              <p className="text-xs font-semibold text-gray-500">
                                Evidence
                              </p>

                              <p className="mt-1 text-sm text-gray-700">
                                &quot;{risk.evidence}&quot;
                              </p>
                            </div>
                          )}
                        </details>
                      )
                    )}
                  </div>
                )}
              </div>

              <div>
                <h3 className="font-semibold">
                  Missing Information
                </h3>

                {analysis.missing_information.length ===
                0 ? (
                  <p className="mt-2 text-sm text-gray-500">
                    No obvious missing information was identified.
                  </p>
                ) : (
                  <div className="mt-3 space-y-3">
                    {analysis.missing_information.map(
                      (item, index) => (
                        <details
                          key={index}
                          className="rounded-lg border border-gray-200 p-4"
                        >
                          <summary className="cursor-pointer font-medium">
                            {item.item}
                          </summary>

                          <p className="mt-3 text-sm text-gray-700">
                            {item.description}
                          </p>

                          {item.evidence && (
                            <div className="mt-3 rounded-lg bg-gray-50 p-3">
                              <p className="text-xs font-semibold text-gray-500">
                                Evidence
                              </p>

                              <p className="mt-1 text-sm text-gray-700">
                                &quot;{item.evidence}&quot;
                              </p>
                            </div>
                          )}
                        </details>
                      )
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
          <div className="chat-header flex items-center justify-between border-b border-gray-200 px-5 py-4">
            <div>
              <h2 className="text-xl font-semibold">
                Document Chat
              </h2>

              <p className="mt-1 text-sm text-gray-600">
                Ask questions and continue the conversation about this document.
              </p>
            </div>

            {chatMessages.length > 0 && (
              <button
                type="button"
                onClick={clearChat}
                disabled={chatSending}
                className="chat-clear-button text-sm text-gray-500 hover:text-black disabled:opacity-50"
              >
                Clear chat
              </button>
            )}
          </div>

          <div
            ref={chatContainerRef}
            className="max-h-[520px] min-h-[260px] space-y-4 overflow-y-auto p-5"
          >
            {chatMessages.length === 0 && (
              <div className="chat-empty-state flex min-h-[220px] items-center justify-center">
                <p className="text-sm text-gray-500">
                  Ask your first question about this document.
                </p>
              </div>
            )}

            {chatMessages.map(
              (chatMessage, index) => (
                <div
                  key={`${chatMessage.role}-${index}`}
                  className={
                    chatMessage.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }
                >
                  <div
                    className={
                      chatMessage.role === "user"
                        ? "chat-bubble-user max-w-[80%] rounded-2xl bg-black px-4 py-3 text-sm text-white"
                        : "chat-bubble-assistant max-w-[85%] rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-800"
                    }
                  >
                    <p className="whitespace-pre-wrap">
                      {chatMessage.content}
                    </p>

                    {chatMessage.role ===
                      "assistant" &&
                      chatMessage.sources &&
                      chatMessage.sources.length >
                        0 && (
                        <details className="mt-4 border-t border-gray-200 pt-3">
                          <summary className="cursor-pointer text-xs font-semibold text-gray-600">
                            Sources (
                            {chatMessage.sources.length}
                            )
                          </summary>

                          <div className="mt-3 space-y-2">
                            {chatMessage.sources.map(
                              (source) => (
                                <div
                                  key={source.source}
                                  className="rounded-lg border border-gray-200 bg-white p-3"
                                >
                                  <p className="text-xs font-semibold text-gray-700">
                                    Source{" "}
                                    {source.source}
                                  </p>

                                  <p className="mt-1 text-xs leading-5 text-gray-600">
                                    {source.content}
                                  </p>
                                </div>
                              )
                            )}
                          </div>
                        </details>
                      )}
                  </div>
                </div>
              )
            )}

            {chatSending && (
              <div className="flex justify-start">
                <div className="chat-thinking rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-500">
                  Thinking...
                </div>
              </div>
            )}
          </div>

          {chatError && (
            <div className="chat-error border-t border-red-200 bg-red-50 px-5 py-3">
              <p className="text-sm text-red-700">
                {chatError}
              </p>
            </div>
          )}

          <form
            onSubmit={handleChatSubmit}
            className="chat-controls border-t border-gray-200 p-4"
          >
            <div className="flex gap-3">
              <textarea
                value={chatInput}
                onChange={(event) =>
                  setChatInput(
                    event.target.value
                  )
                }
                placeholder="Ask about this document..."
                rows={2}
                disabled={chatSending}
                className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none focus:border-black disabled:bg-gray-100"
              />

              <button
                type="submit"
                disabled={
                  chatSending ||
                  !chatInput.trim()
                }
                className="self-end rounded-xl bg-black px-5 py-3 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {chatSending
                  ? "Sending..."
                  : "Send"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}
