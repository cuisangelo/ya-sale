"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchUsage } from "../../lib/api";
import { usageStats, type UsageState } from "../../lib/landing";
import styles from "../../app/landing.module.css";

export function UsageProof() {
  const [state, setState] = useState<UsageState>({ status: "loading" });

  useEffect(() => {
    let ignore = false;
    fetchUsage().then(
      (usage) => {
        if (!ignore) setState({ status: "ready", usage });
      },
      (caught: unknown) => {
        // The block is optional proof: hide it instead of breaking the landing.
        console.error("Usage stats unavailable", caught);
        if (!ignore) setState({ status: "failed" });
      },
    );
    return () => {
      ignore = true;
    };
  }, []);

  const stats = usageStats(state);
  if (!stats) return null;

  return (
    <section className={styles.section} aria-labelledby="uso-titulo">
      <p className="eyebrow" id="uso-titulo">
        En vivo, desde la base de datos
      </p>
      <div className={`stats-grid ${styles.stats}`}>
        {stats.map((stat) => (
          <article key={stat.label} className={`stat bar-${stat.tone}`}>
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
          </article>
        ))}
      </div>
      <p className="footnote">
        Sin cuentas del equipo ni tráfico automatizado. <Link href="/uso/">Ver el uso en vivo →</Link>
      </p>
    </section>
  );
}
