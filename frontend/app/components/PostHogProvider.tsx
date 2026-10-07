"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { identifyUser, initPostHog, trackPageView } from "../lib/analytics";

export default function PostHogProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const prevPathname = useRef<string | null>(null);

  useEffect(() => {
    initPostHog();
    identifyUser();
  }, []);

  useEffect(() => {
    if (pathname === prevPathname.current) return;
    prevPathname.current = pathname;
    trackPageView(pathname);
  }, [pathname]);

  return <>{children}</>;
}
