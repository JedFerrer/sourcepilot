import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "SourcePilot",
  description: "AI-assisted supplier sourcing workspace",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-theme="light">
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <nav aria-label="Legal information" className="mx-auto flex max-w-[1440px] justify-end px-4 sm:px-8">
          <a className="inline-flex min-h-11 items-center py-2 text-sm underline" href="/legal.html" target="_blank" rel="noopener noreferrer">
            Legal / Licenses (opens in a new tab)
          </a>
        </nav>
        {children}
      </body>
    </html>
  );
}
