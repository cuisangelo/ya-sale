import type { Metadata } from "next";
import { HomeTop } from "../components/landing/HomeTop";
import { McpUrl } from "../components/landing/McpUrl";
import styles from "./landing.module.css";

const TITLE = "Ya Sale · Tu viaje por el Perú, tramo por tramo";
const DESCRIPTION =
  "Escribe de dónde a dónde vas y ve el viaje completo en bus, avión, tren, colectivo, combi, mototaxi o lancha, con la fuente y la fecha de cada dato.";
const SHARE_IMAGE = {
  url: "/og-image.png",
  width: 1200,
  height: 630,
  alt: "Ya Sale: ¿de dónde a dónde vas? Tu viaje a cualquier punto del Perú, tramo por tramo.",
};

// Share crawlers need absolute URLs; this is the public domain the LinkedIn post links to.
export const metadata: Metadata = {
  metadataBase: new URL("https://yasale.cuisangelo.com"),
  title: TITLE,
  description: DESCRIPTION,
  openGraph: {
    type: "website",
    locale: "es_PE",
    siteName: "Ya Sale",
    url: "/",
    title: TITLE,
    description: DESCRIPTION,
    images: [SHARE_IMAGE],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: [SHARE_IMAGE],
  },
};

export default function HomePage() {
  return (
    <main className={styles.home}>
      <HomeTop />

      <section id="agentes" className={`${styles.column} ${styles.agents}`} aria-labelledby="agentes-titulo">
        <h2 id="agentes-titulo" className={styles.heading}>
          Para agentes
        </h2>
        <p>
          Ya Sale también es un servidor MCP: pega esta URL como conector en ChatGPT o Claude y tu chat arma el
          viaje con las mismas fuentes y fechas que esta página.
        </p>
        <McpUrl />
      </section>

      <footer className={`footer-row ${styles.column} ${styles.footer}`}>
        <a href="https://github.com/cuisangelo/ya-sale">Código en GitHub</a>
      </footer>
    </main>
  );
}
