"use client";

import styles from "../../app/landing.module.css";
import { useOpenTrip } from "./useOpenTrip";

interface Route {
  origin: string;
  destination: string;
  photo: string;
  alt: string;
  credit: { author: string; license: string; page: string };
}

// Photos from Wikimedia Commons under free licenses; the credit line is a license requirement.
const ROUTES: Route[] = [
  {
    origin: "Cusco",
    destination: "Aguas Calientes",
    photo: "/landing/cusco-aguas-calientes.jpg",
    alt: "Tren azul en la estación de Aguas Calientes",
    credit: {
      author: "Jorge Láscar",
      license: "CC BY 2.0",
      page: "https://commons.wikimedia.org/wiki/File:Lascar_Vistadome_railway_car_at_the_Aguas_Calientes_train_station_(4548130275).jpg",
    },
  },
  {
    origin: "Iquitos",
    destination: "Nauta",
    photo: "/landing/iquitos-nauta.jpg",
    alt: "Nauta y sus embarcaciones a orillas del río Marañón",
    credit: {
      author: "Maurice Chédel",
      license: "CC BY 3.0",
      page: "https://commons.wikimedia.org/wiki/File:Nauta-Loreto-Peru.JPG",
    },
  },
  {
    origin: "Lima",
    destination: "Sauce",
    photo: "/landing/lima-sauce.jpg",
    alt: "Embarcadero de la Laguna de Sauce, San Martín",
    credit: {
      author: "Pitxiquin",
      license: "CC BY-SA 4.0",
      page: "https://commons.wikimedia.org/wiki/File:Port_de_Sauce_a_la_Laguna_de_Sauce_a_la_prov%C3%ADncia_de_San_Mart%C3%ADn.jpg",
    },
  },
  {
    origin: "Arequipa",
    destination: "Chivay",
    photo: "/landing/arequipa-chivay.jpg",
    alt: "Cañón del Colca, cerca de Chivay",
    credit: {
      author: "Nad Hemnani",
      license: "CC0",
      page: "https://commons.wikimedia.org/wiki/File:Colca_Canyon,_Chivay,_Peru_(Unsplash).jpg",
    },
  },
];

export function RouteCards({ className }: { className: string }) {
  const openTrip = useOpenTrip();

  return (
    <section className={className} aria-labelledby="rutas-titulo">
      <p className="eyebrow" id="rutas-titulo">
        Prueba con una ruta del Perú
      </p>
      <ul className={styles.routes}>
        {ROUTES.map((route) => (
          <li key={route.photo}>
            <figure className={styles.route}>
              <button type="button" className={styles.routeButton} onClick={() => openTrip(route.origin, route.destination)}>
                <img src={route.photo} alt={route.alt} width={800} height={600} />
                <span className={styles.routeName}>
                  {route.origin} → {route.destination}
                </span>
                <span className={styles.routeCta}>Armar este viaje →</span>
              </button>
              <figcaption className={styles.credit}>
                Foto:{" "}
                <a href={route.credit.page} target="_blank" rel="noreferrer">
                  {route.credit.author} · {route.credit.license}
                </a>
              </figcaption>
            </figure>
          </li>
        ))}
      </ul>
    </section>
  );
}
