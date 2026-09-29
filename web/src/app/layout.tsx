import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jyotish Platform",
  description: "Precise Vedic astrology with transparent calculations and classical sources.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
