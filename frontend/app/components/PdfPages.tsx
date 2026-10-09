"use client";

import { useEffect, useRef, useState } from "react";

type Status = "loading" | "ready" | "error";

// Draws every page of a PDF onto canvases with pdf.js, so the document shows
// in browsers that can't display a PDF inside an iframe (Android Chrome).
export default function PdfPages({ url, title }: { url: string; title: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let destroyLoadingTask: (() => void) | null = null;

    async function render(target: HTMLDivElement) {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          "pdfjs-dist/build/pdf.worker.min.mjs",
          import.meta.url,
        ).toString();

        const loadingTask = pdfjs.getDocument({ url });
        destroyLoadingTask = () => loadingTask.destroy();
        const pdf = await loadingTask.promise;

        const cssWidth = target.clientWidth || 360;
        const pixelRatio = window.devicePixelRatio || 1;

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          if (cancelled) return;
          const page = await pdf.getPage(pageNumber);
          const scale = cssWidth / page.getViewport({ scale: 1 }).width;
          const viewport = page.getViewport({ scale: scale * pixelRatio });

          const canvas = document.createElement("canvas");
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          canvas.className = "pdf-page block h-auto w-full border-b border-gray-200";
          canvas.setAttribute("role", "img");
          canvas.setAttribute(
            "aria-label",
            `${title}, page ${pageNumber} of ${pdf.numPages}`,
          );
          target.appendChild(canvas);

          await page.render({ canvas, viewport }).promise;
          if (pageNumber === 1 && !cancelled) setStatus("ready");
        }
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    render(container);

    return () => {
      cancelled = true;
      destroyLoadingTask?.();
      container.replaceChildren();
    };
  }, [url, title]);

  return (
    <div className="pdf-pages bg-gray-100">
      {status === "loading" && (
        <p className="p-5 text-sm text-gray-500">Loading document preview...</p>
      )}

      {status === "error" && (
        <p className="pdf-pages-error p-5 text-sm text-gray-600">
          The document preview couldn&apos;t be shown. Please reload the page.
        </p>
      )}

      <div ref={containerRef} />
    </div>
  );
}
