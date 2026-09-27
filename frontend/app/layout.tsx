import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import AuthNav from "./components/AuthNav";
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
      <body className="min-h-screen flex flex-col pb-12">
        <AuthNav />

        <div className="flex-1">
          {children}
        </div>

        <footer className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white px-6 py-2 text-center text-xs text-gray-500">
          This tool provides AI-assisted document analysis and is not a
          substitute for professional legal advice.
        </footer>
      </body>
    </html>
  );
}