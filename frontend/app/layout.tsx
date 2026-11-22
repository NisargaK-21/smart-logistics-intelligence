import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "../lib/context";
import AppShell from "../components/AppShell";

export const metadata: Metadata = {
  title: "NER-ResQ — Smart Logistics Intelligence",
  description:
    "AI-powered, disaster-resilient logistics for the Northeast Region of India.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col bg-[#F9F6F0] text-[#1E2E28] selection:bg-[#E8DFD1] selection:text-[#182822]">
        <AppProvider>
          <AppShell>{children}</AppShell>
        </AppProvider>
      </body>
    </html>
  );
}
