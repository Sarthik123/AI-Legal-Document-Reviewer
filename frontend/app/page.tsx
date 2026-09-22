export default function Home() {
  return (
    <main className="min-h-screen bg-white text-gray-900">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 text-center">
        <div className="mb-6 rounded-full bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700">
          AI Legal Document Reviewer
        </div>

        <h1 className="max-w-4xl text-5xl font-bold tracking-tight sm:text-6xl">
          Understand your legal documents with confidence.
        </h1>

        <p className="mt-6 max-w-2xl text-lg leading-8 text-gray-600">
          Upload a legal document, identify important risks and missing
          information, and ask questions using answers grounded in your
          document.
        </p>

        <div className="mt-10 flex flex-col gap-4 sm:flex-row">
          <a
            href="/upload"
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700"
          >
            Review a Document
          </a>

          <button className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50">
            Learn More
          </button>
        </div>

        <p className="mt-8 max-w-xl text-sm text-gray-500">
          AI assistance for document understanding. This tool does not provide
          legal advice or replace a qualified legal professional.
        </p>
      </section>
    </main>
  );
}