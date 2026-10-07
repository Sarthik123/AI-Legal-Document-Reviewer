export default function PrivacyPage() {
  return (
    <main className="app-page mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-3xl font-bold">Privacy at Lawyer Lens</h1>
      <p className="mt-2 text-sm text-gray-500">Last updated: 7 Oct 2026</p>

      <dl className="mt-8 space-y-6 text-gray-700">
        <div>
          <dt className="font-semibold">What we collect</dt>
          <dd className="mt-1">
            Your email, the documents you upload, and the questions you ask.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Why</dt>
          <dd className="mt-1">
            Only to review your documents and answer your questions.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Who can see your documents</dt>
          <dd className="mt-1">
            Only you. We never sell or share your data.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Where it&apos;s stored</dt>
          <dd className="mt-1">
            Your files are stored privately in Cloudflare R2, and your account
            and document data in our database (Neon).
          </dd>
        </div>

        <div>
          <dt className="font-semibold">AI processing</dt>
          <dd className="mt-1">
            Your document text is sent to Cloudflare Workers AI to create your
            review and answers.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Email</dt>
          <dd className="mt-1">
            We use Brevo only to send account emails (like verification). It
            never receives your documents.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Analytics</dt>
          <dd className="mt-1">
            We use PostHog to count actions like &ldquo;uploaded a
            document&rdquo;, using an internal ID. We never send your email,
            document text, file names, questions, or answers to analytics.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Deleting your data</dt>
          <dd className="mt-1">
            You can delete any document anytime. This removes the file, its
            contents, and its chats. Backup copies are fully removed within 6
            hours.
          </dd>
        </div>

        <div>
          <dt className="font-semibold">Contact</dt>
          <dd className="mt-1">
            <a
              href="mailto:sarthik.bhan@gmail.com"
              className="text-blue-600 underline hover:text-blue-800"
            >
              sarthik.bhan@gmail.com
            </a>
          </dd>
        </div>
      </dl>
    </main>
  );
}
