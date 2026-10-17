import type { Metadata } from "next";
import localFont from "next/font/local";
import { Franja } from "../components/Franja";
import "../styles/tokens.css";
import "../styles/app.css";

// Self-hosted (OFL, latin subset) so the build never depends on fetching Google Fonts.
const bricolage = localFont({
  src: "./fonts/BricolageGrotesque-800-latin.woff2",
  weight: "800",
  variable: "--font-bricolage",
  display: "swap",
});

const archivo = localFont({
  src: "./fonts/Archivo-latin.woff2",
  weight: "100 900",
  variable: "--font-archivo",
  display: "swap",
});

const jetbrains = localFont({
  src: "./fonts/JetBrainsMono-latin.woff2",
  weight: "400 800",
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Ya Sale",
  description: "Tu viaje a cualquier punto del Perú, tramo por tramo.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${bricolage.variable} ${archivo.variable} ${jetbrains.variable}`}>
      <body>
        <Franja />
        <div className="page">{children}</div>
        <Franja />
      </body>
    </html>
  );
}
