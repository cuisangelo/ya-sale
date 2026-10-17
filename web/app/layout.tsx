import type { Metadata } from "next";
import { Archivo, Bricolage_Grotesque, JetBrains_Mono } from "next/font/google";
import { Franja } from "../components/Franja";
import "../styles/tokens.css";
import "../styles/app.css";

const bricolage = Bricolage_Grotesque({
  weight: "800",
  subsets: ["latin"],
  variable: "--font-bricolage",
  display: "swap",
});

const archivo = Archivo({
  weight: ["400", "600", "700", "800"],
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  weight: ["400", "600"],
  subsets: ["latin"],
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
