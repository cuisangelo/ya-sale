"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchRecentTrips, type RecentTrip } from "../../lib/api";
import { relativeTime } from "../../lib/format";
import { limaToday, tripHref } from "../../lib/landing";
import { DestinationHero } from "../DestinationHero";
import { Logo } from "../Logo";
import { RecentSearches, type RecentSearch } from "./RecentSearches";
import { TripForm } from "./TripForm";
import styles from "../../app/landing.module.css";

type Recent = { searches: RecentSearch[]; now: number };

function recentSearch(trip: RecentTrip, today: string): RecentSearch {
  const result = tripHref({ origin: trip.origin, destination: trip.destination, date: today }, today);
  if (!result.ok) throw new Error(`Invalid recent trip ${trip.origin} → ${trip.destination}: ${result.error}`);
  return { trip, href: result.href };
}

export function HomeTop() {
  const [recent, setRecent] = useState<Recent | null>(null);

  useEffect(() => {
    let current = true;
    fetchRecentTrips()
      .then((trips) => {
        const today = limaToday(new Date());
        const searches = trips.map((trip) => recentSearch(trip, today));
        if (current) setRecent({ searches, now: Date.now() });
      })
      .catch((error: unknown) => {
        // Without real searches the hero keeps its gradient and the section stays out: nothing is invented.
        console.error("Recent searches unavailable", error);
      });
    return () => {
      current = false;
    };
  }, []);

  const latest = recent?.searches[0]?.trip ?? null;
  return (
    <>
      <DestinationHero
        place={latest?.place ?? null}
        point={latest ? [latest.lat, latest.lng] : null}
        height="home"
        nav={
          <nav className={styles.nav} aria-label="Principal">
            <Logo inverted />
            <span className={styles.navLinks}>
              <Link href="/comparar/">Comparar</Link>
              <Link href="/uso/">Uso real</Link>
              <a href="#agentes">Para agentes</a>
            </span>
          </nav>
        }
      >
        {latest && recent && (
          <p className={styles.pill}>
            <span className={styles.pillDot} aria-hidden="true" />
            <span className={styles.pillText}>
              Última búsqueda: {latest.origin} → {latest.destination}, {relativeTime(latest.at, recent.now)}
            </span>
          </p>
        )}
        <h1 className={styles.claim}>¿De dónde a dónde vas?</h1>
        <p className={styles.lede}>Cualquier punto del Perú, tramo por tramo, con precio, fuente y fecha.</p>
      </DestinationHero>
      <div className={styles.column}>
        <div id="viaje" className={styles.searchWrap}>
          <TripForm />
        </div>
        {recent && <RecentSearches searches={recent.searches} now={recent.now} />}
      </div>
    </>
  );
}
