export default function UploadPage() {
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

          <button className="mt-6 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700">
            Choose PDF
          </button>
        </div>

        <p className="mt-6 text-center text-sm text-gray-500">
          Your document will be used only to provide document analysis.
          AI-generated information does not constitute legal advice.
        </p>
      </section>
    </main>
  );
}