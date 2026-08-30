"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/Icon";
import { PlotBar } from "@/components/PlotBar";

const LINKS = [
  { href: "/", label: "Plot" },
  { href: "/water", label: "Water" },
  { href: "/health", label: "Leaf" },
  { href: "/assistant", label: "Ask" },
  { href: "/records", label: "Records" },
  { href: "/evidence", label: "Evidence" },
];

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <div className="page-shell site-header__inner">
        <Link href="/" className="brand">
          <span className="brand__mark" aria-hidden="true">
            <Icon name="rice" size={24} />
          </span>
          <span className="brand__name">
            IRIS
            <small>Intelligent Rice Integrated System</small>
          </span>
        </Link>
        <nav className="nav" aria-label="Main">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={isCurrent(pathname, l.href) ? "page" : undefined}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
      <PlotBar />
    </header>
  );
}
