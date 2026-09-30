"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  clearAccessToken,
  getLoggedInSnapshot,
  getServerSnapshot,
  subscribeToAuthState,
} from "../auth";

export default function AuthNav() {
  const router = useRouter();
  const loggedIn = useSyncExternalStore(
    subscribeToAuthState,
    getLoggedInSnapshot,
    getServerSnapshot,
  );

  if (!loggedIn) {
    return null;
  }

  function handleLogout() {
    clearAccessToken();
    router.push("/login");
  }

  return (
    <header className="app-nav">
      <div className="app-brand" aria-label="AI Legal Document Reviewer">
        <span className="app-brand-mark" aria-hidden="true">L</span>
        <span>AI Legal Reviewer</span>
      </div>

      <nav className="app-nav-actions" aria-label="Account navigation">
        <Link href="/dashboard">Dashboard</Link>
        <button type="button" onClick={handleLogout}>Logout</button>
      </nav>
    </header>
  );
}
