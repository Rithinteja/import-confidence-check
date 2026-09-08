import type { Metadata } from "next";
import { Figtree } from "next/font/google";
import AppShell from "@/components/AppShell";
import "./globals.css";

const figtree = Figtree({
  variable: "--font-figtree",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Import Confidence Check",
  description: "Import Confidence Check prototype",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${figtree.variable} ${figtree.className}`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
