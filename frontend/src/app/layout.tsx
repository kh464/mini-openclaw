import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import { StoreProvider } from "@/lib/store";

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
        <StoreProvider>
          <Navbar />
          <main className="h-[calc(100vh-3.5rem)]">{children}</main>
        </StoreProvider>
      </body>
    </html>
  );
}
