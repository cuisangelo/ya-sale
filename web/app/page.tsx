import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "../components/Logo";
import { McpUrl } from "../components/landing/McpUrl";
import { TripForm } from "../components/landing/TripForm";
import { UsageProof } from "../components/landing/UsageProof";
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

const STEPS = [
  {
    motif: "mayu",
    title: "Busca en vivo",
    text: "Cada consulta sale a buscar en la web en ese momento. Lo que ya está guardado es solo el punto de partida.",
  },
  {
    motif: "chakana",
    title: "Tramo por tramo, con fuente y fecha",
    text: "Ves el viaje en el orden en que se hace: de dónde sale, cuánto cuesta y cuánto demora, con el link a la fuente y la fecha de consulta.",
  },
  {
    motif: "chaska",
    title: "Lo confirma quien lo hace",
    text: "Quien viaja la ruta confirma o corrige el tramo. Ningún tramo aparece como confirmado si ninguna persona lo confirmó.",
  },
] as const;

export default function HomePage() {
  return (
    <main className={`shell ${styles.landing}`}>
      <section className={styles.hero} id="viaje" aria-labelledby="promesa">
        <Logo />
        <h1 id="promesa" className={styles.promise}>
          Tu viaje a cualquier punto del Perú, tramo por tramo.
        </h1>
        <p className={styles.modes}>
          Bus, avión, tren, colectivo, combi, mototaxi o lancha, con la fuente y la fecha de cada dato.
        </p>
        <TripForm />
      </section>

      <UsageProof />

      <section className={styles.section} aria-labelledby="como-titulo">
        <h2 id="como-titulo" className={styles.heading}>
          Cómo funciona
        </h2>
        <ol className={styles.steps}>
          {STEPS.map((step, index) => (
            <li key={step.title} className={styles.step}>
              <span className={`${styles.motif} ${styles[step.motif]}`} aria-hidden="true" />
              <div>
                <h3 className={styles.stepTitle}>
                  <span className="mono">{index + 1}.</span> {step.title}
                </h3>
                <p>{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className={`${styles.section} ${styles.lastMile}`} aria-labelledby="pueblo-titulo">
        <h2 id="pueblo-titulo" className={styles.heading}>
          ¿Tu pueblo está al final del camino?
        </h2>
        <p>
          El último tramo casi nunca está en internet: el colectivo que sale cuando llena, la combi del
          mercado, la lancha del puerto. Arma el viaje hasta tu pueblo y, si conoces ese tramo, confírmalo o
          corrígelo. Así el siguiente que viaje no tiene que preguntar en el paradero.
        </p>
        <a className={`btn ${styles.lastMileButton}`} href="#viaje">
          Armar el viaje a mi pueblo
        </a>
      </section>

      <section className={styles.section} aria-labelledby="mcp-titulo">
        <h2 id="mcp-titulo" className={styles.heading}>
          Úsalo desde ChatGPT o Claude
        </h2>
        <p>Ya Sale también es un servidor MCP: tu chat arma el viaje con las mismas fuentes y fechas que esta página.</p>
        <ol className={styles.howTo}>
          <li>
            Copia la URL del conector:
            <McpUrl />
          </li>
          <li>En Claude o ChatGPT, agrega un conector personalizado (MCP remoto) y pega esa URL.</li>
          <li>
            Pregúntale, por ejemplo: <i>«¿Cómo llego de Cusco a Aguas Calientes el sábado?»</i>
          </li>
        </ol>
        <p className="footnote">
          Herramientas: <code>plan_trip</code>, <code>get_leg</code> y <code>confirm_leg</code>.{" "}
          <Link href="/comparar/">Mira el mismo chat con y sin Ya Sale →</Link>
        </p>
      </section>

      <footer className="footer-row">
        <Link href="/comparar/">Comparación →</Link>
        <Link href="/uso/">Uso en vivo →</Link>
        <a href="https://github.com/cuisangelo/ya-sale">Código en GitHub →</a>
      </footer>
    </main>
  );
}
