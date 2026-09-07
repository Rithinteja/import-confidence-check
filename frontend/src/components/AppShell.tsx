"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

type NavItem = { label: string; href: string };

const navItems: NavItem[] = [
  { label: "Home", href: "/" },
  { label: "Catalog", href: "/catalog" },
  { label: "Data Ingestion", href: "/" },
  { label: "README", href: "/readme" },
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.label === "Catalog") return pathname.startsWith("/catalog");
  if (item.label === "README") return pathname.startsWith("/readme");
  if (item.label === "Data Ingestion") {
    return (
      !pathname.startsWith("/catalog") &&
      !pathname.startsWith("/readme") &&
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
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    const saved = window.localStorage.getItem("sidebar-open");
    if (saved === "0") setSidebarOpen(false);
  }, []);

  function toggleSidebar() {
    setSidebarOpen((open) => {
      const next = !open;
      window.localStorage.setItem("sidebar-open", next ? "1" : "0");
      return next;
    });
  }

  return (
    <div className={`app-shell ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
      <header className="topbar">
        <button
          className="sidebar-toggle"
          type="button"
          aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          aria-expanded={sidebarOpen}
          onClick={toggleSidebar}
        >
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
            <rect
              x="1.5"
              y="2.5"
              width="13"
              height="11"
              rx="1.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.25"
            />
            <path d="M5.5 2.5v11" fill="none" stroke="currentColor" strokeWidth="1.25" />
          </svg>
        </button>
        <Link className="brand" href="/">
          <svg viewBox="0 0 34 34" aria-hidden="true">
            <path d="M17 2 31 10 17 18 3 10 17 2Z" fill="#ff3621" />
            <path
              d="m4 15 13 7 13-7v4l-13 7L4 19v-4Zm0 8 13 7 13-7v4l-13 7L4 27v-4Z"
              fill="#ff3621"
            />
          </svg>
          <span className="brand-text">
            <span className="brand-name">databricks</span>
            <span className="brand-edition">Free Edition</span>
          </span>
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
            DB
          </button>
        </div>
      </header>

      <aside className="sidebar" aria-hidden={!sidebarOpen}>
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
          Prototype · Postgres storage · file scanner · Groq explanations
        </p>
      </aside>

      <main className="main-area">{children}</main>
    </div>
  );
}
