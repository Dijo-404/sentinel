import type { Metadata } from "next";
import { ShellProvider } from "@/adapters/shell-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sentinel web shell",
  description: "SN-012 customer and operator console (web-shell.v1)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ShellProvider>{children}</ShellProvider>
      </body>
    </html>
  );
}
