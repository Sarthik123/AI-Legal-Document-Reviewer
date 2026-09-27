"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export default function AuthNav() {
  const router = useRouter();
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(Boolean(localStorage.getItem("access_token")));
  }, [pathname]);

  if (!loggedIn) {
    return null;
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    setLoggedIn(false);
    router.push("/login");
  }

  return (
    <div className="flex items-center justify-end gap-3 px-6 py-4">
      <Link
        href="/dashboard"
        className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        Dashboard
      </Link>

      <button
        type="button"
        onClick={handleLogout}
        className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
      >
        Logout
      </button>
    </div>
  );
}