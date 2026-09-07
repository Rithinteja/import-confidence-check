"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavItem = { label: string; href: string };

const navItems: NavItem[] = [
  { label: "Home", href: "/" },
  { label: "Catalog", href: "/catalog" },
  { label: "Data Ingestion", href: "/" },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.label === "Catalog") return pathname.startsWith("/catalog");
  if (item.label === "Data Ingestion") {
    return (
      !pathname.startsWith("/catalog") &&
      (pathname === "/" ||
        pathname.startsWith("/create-table") ||
        pathname.startsWith("/add-data"))
    );
  }
  if (item.label === "Home") {
    return pathname === "/" || pathname.startsWith("/add-data");
  }
  return pathname === item.href;
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <svg viewBox="0 0 34 34" aria-hidden="true">
            <path d="M17 2 31 10 17 18 3 10 17 2Z" fill="#ff3621" />
            <path
              d="m4 15 13 7 13-7v4l-13 7L4 19v-4Zm0 8 13 7 13-7v4l-13 7L4 27v-4Z"
              fill="#ff3621"
            />
          </svg>
          <span>databricks</span>
        </Link>
        <div className="global-search" role="search">
          <span className="search-hint">
            Search data, notebooks, recents, and more...
          </span>
          <kbd>CTRL + P</kbd>
        </div>
        <div className="top-actions">
          <button className="verify" type="button">
            Verify identity
          </button>
          <button className="workspace-switcher" type="button">
            workspace
          </button>
          <button className="avatar" type="button" aria-label="Account">
            R
          </button>
        </div>
      </header>

      <aside className="sidebar">
        <Link className="new-button" href="/">
          + New
        </Link>
        <nav aria-label="Primary">
          <div className="nav-group">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className={`nav-item ${isActive(pathname, item) ? "active" : ""}`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
        <p className="prototype-label">
          Any CSV/JSON/Excel · Groq explanations · Catalog lists created tables
        </p>
      </aside>

      <main className="main-area">{children}</main>
    </div>
  );
}
