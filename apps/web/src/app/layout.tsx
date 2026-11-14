import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ShellProvider } from "@/adapters/shell-context";
import { Cursor } from "@/components/cursor";
import "./globals.css";
import "./premium.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sentinel web shell",
  description:
    "SN-038 six role portals + SN-012 intake/ops shell (web-shell.v1)",
  icons: { icon: "/brand/sentinel-mark.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <ShellProvider>{children}</ShellProvider>
        <Cursor />
      </body>
    </html>
  );
}
