import type { Metadata } from "next";
import localFont from "next/font/local";
import "../styles/tokens.css";
import "../styles/app.css";

// Self-hosted (OFL, latin subset) so the build never depends on fetching Google Fonts.
const inter = localFont({
  src: "./fonts/Inter-latin.woff2",
  weight: "100 900",
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Ya Sale",
  description: "Tu viaje a cualquier punto del Perú, tramo por tramo.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={inter.variable}>
      <body>
        <div className="page">{children}</div>
      </body>
    </html>
  );
}
