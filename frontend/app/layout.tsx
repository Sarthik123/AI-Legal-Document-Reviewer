import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import AuthNav from "./components/AuthNav";
import PostHogProvider from "./components/PostHogProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Legal Document Reviewer",
  description: "AI-assisted legal document analysis",
};

type LayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: LayoutProps) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-screen flex-col">
        <PostHogProvider>
          <AuthNav />

          <div className="flex-1">
            {children}
          </div>

          <footer className="app-footer">
            This tool provides AI-assisted document analysis and is not a
            substitute for professional legal advice.{" "}
            <a href="/privacy" className="underline hover:text-gray-500">
              Privacy
            </a>
            {" · "}
            <a
              href="https://forms.gle/1vYLhWUrbvcZm3vw9"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-500"
            >
              Give feedback
            </a>
          </footer>
        </PostHogProvider>
      </body>
    </html>
  );
}
