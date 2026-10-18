"use client";

import { useEffect, useState, type ReactNode } from "react";
import { destinationPhoto, type Photo } from "../lib/photos";

interface DestinationHeroProps {
  place: string | null;
  point: [number, number] | null;
  height: "home" | "trip";
  nav: ReactNode;
  children: ReactNode;
}

export function DestinationHero({ place, point, height, nav, children }: DestinationHeroProps) {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [loaded, setLoaded] = useState(false);
  const lat = point?.[0];
  const lon = point?.[1];

  useEffect(() => {
    setPhoto(null);
    setLoaded(false);
    if (!place || lat === undefined || lon === undefined) return;
    let current = true;
    destinationPhoto(place, [lat, lon])
      .then((found) => {
        if (current) setPhoto(found);
      })
      .catch((error: unknown) => {
        if (current) console.error("Destination photo lookup failed", error);
      });
    return () => {
      current = false;
    };
  }, [place, lat, lon]);

  return (
    <header className={`dest-hero dest-hero-${height}`}>
      {photo && (
        <img
          className={`dest-hero-photo${loaded ? " is-loaded" : ""}`}
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
      <div className="dest-hero-overlay" />
      <div className="dest-hero-nav">{nav}</div>
      <div className="dest-hero-content">{children}</div>
      {photo && loaded && (
        <a className="dest-hero-credit" href={photo.page} target="_blank" rel="noreferrer">
          Foto: {photo.author} · {photo.license} · Wikimedia Commons
        </a>
      )}
    </header>
  );
}
