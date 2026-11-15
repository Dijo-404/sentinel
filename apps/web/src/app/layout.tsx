import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { ShellProvider } from "@/adapters/shell-context";
import { Cursor } from "@/components/cursor";
import "./tokens.css";
import "./globals.css";
import "./premium.css";
import "./ledger.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-grotesk",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Sentinel — every refund, from complaint to confirmed credit",
  description: "SN-038 six role portals + SN-012 intake/ops shell (web-shell.v1)",
  icons: { icon: "/brand/sentinel-mark.svg" },
};

// Runs before paint so a saved Paper theme never flashes dark first.
const THEME_BOOT = `try{var t=localStorage.getItem("sentinel-theme");if(t==="light")document.documentElement.dataset.theme="light"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${grotesk.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body>
        <ShellProvider>{children}</ShellProvider>
        <Cursor />
      </body>
    </html>
  );
}
