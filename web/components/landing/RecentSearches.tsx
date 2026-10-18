"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { RecentTrip } from "../../lib/api";
import { relativeTime } from "../../lib/format";
import type { RecentSearch } from "../../lib/landing";
import { destinationPhoto, type Photo } from "../../lib/photos";
import styles from "../../app/landing.module.css";

export function RecentSearches({ searches, now }: { searches: RecentSearch[]; now: number }) {
  if (searches.length === 0) return null;
  return (
    <section className={styles.recent} aria-labelledby="recientes-titulo">
      <div className={styles.recentHead}>
        <h2 id="recientes-titulo" className={styles.heading}>
          Lo último que la gente buscó
        </h2>
        <span className={styles.note}>Búsquedas reales · toca una para verla</span>
      </div>
      <ul className={styles.recentGrid}>
        {searches.map(({ trip, href }) => (
          <RecentCard key={`${trip.origin}|${trip.destination}`} trip={trip} href={href} now={now} />
        ))}
      </ul>
    </section>
  );
}

function RecentCard({ trip, href, now }: { trip: RecentTrip; href: string; now: number }) {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let current = true;
    destinationPhoto(trip.place, [trip.lat, trip.lng])
      .then((found) => {
        if (current) setPhoto(found);
      })
      .catch((error: unknown) => {
        if (current) console.error("Destination photo lookup failed", error);
      });
    return () => {
      current = false;
    };
  }, [trip.place, trip.lat, trip.lng]);

  const title = `${trip.origin} → ${trip.destination}`;
  return (
    <li className={styles.recentCard}>
      <Link href={href} className={styles.recentLink}>
        <span className={styles.recentPhoto}>
          {photo && (
            <img
              className={loaded ? styles.isLoaded : undefined}
              src={photo.url}
              alt=""
              referrerPolicy="no-referrer"
              onLoad={() => setLoaded(true)}
              onError={() => {
                console.error("Destination photo failed to load", photo.url);
                setPhoto(null);
              }}
            />
          )}
        </span>
        <span className={styles.recentBody}>
          <b className={styles.recentTitle} title={title}>
            {title}
          </b>
          <span className={styles.note}>{relativeTime(trip.at, now)}</span>
        </span>
      </Link>
      {photo && loaded && (
        <a className={styles.recentCredit} href={photo.page} target="_blank" rel="noreferrer">
          Foto: {photo.author} · {photo.license}
        </a>
      )}
    </li>
  );
}
