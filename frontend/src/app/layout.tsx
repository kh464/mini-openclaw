import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "mini OpenClaw",
  description: "AI Agent Teaching & Research System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">
        <Navbar />
        <main className="h-[calc(100vh-3.5rem)]">{children}</main>
      </body>
    </html>
  );
}
