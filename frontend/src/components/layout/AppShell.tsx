"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
];

function isSplitPanelRoute(pathname: string) {
  return /^\/documents\/[^/]+\/(summary|chat)\/?$/.test(pathname);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const splitPanel = isSplitPanelRoute(pathname);

  return (
    <div
      className={`flex min-h-screen flex-col bg-surface-muted text-ink ${
        splitPanel ? "h-screen overflow-hidden" : ""
      }`}
    >
      <header className="shrink-0 border-b border-surface-border bg-surface">
        <div className="flex w-full items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              RFQ / RFP Platform
            </p>
            <h1 className="text-lg font-semibold">Document Intelligence</h1>
          </div>
          <nav className="flex gap-6 text-sm">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-ink-muted transition hover:text-ink"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main
        className={
          splitPanel
            ? "flex min-h-0 flex-1 flex-col overflow-hidden"
            : "w-full px-4 py-6 sm:px-6 lg:px-8"
        }
      >
        {children}
      </main>
    </div>
  );
}
