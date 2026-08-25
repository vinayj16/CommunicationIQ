import type { Metadata } from "next";
import { Bricolage_Grotesque, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { RoleProvider } from "@/components/RoleProvider";
import { ThemeProvider } from "@/components/ThemeProvider";

/* Typefaces for the Campus theme.
 *
 *  Loaded through next/font rather than a <link> to fonts.googleapis.com, and
 *  that is not a preference. These get downloaded at build time and served
 *  from our own origin, so the theme still renders on a laptop running a
 *  smoke test on a LAN with no internet — which is exactly the situation the
 *  product is tested in. A Google Fonts link would silently fall back to
 *  system-ui there and the theme would look like a different theme.
 *
 *  `display: swap` so text is readable immediately rather than invisible
 *  while a face loads. Only the weights actually used are requested.
 */
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
  variable: "--font-campus-display",
  display: "swap",
});

const body = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-campus-body",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-campus-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fluenzee AI",
  description:
    "Placement-readiness assessment and training — simulate the real test, diagnose the real gap.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="campus"
      className={`${display.variable} ${body.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider>
          <RoleProvider>{children}</RoleProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
