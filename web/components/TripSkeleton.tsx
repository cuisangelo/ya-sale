import { LoadingWords } from "./LoadingWords";

export function TripSkeleton({ origin, destination }: { origin: string; destination: string }) {
  return (
    <section className="trip-skeleton" aria-busy="true" aria-label="Armando tu viaje">
      <div className="loom" aria-hidden="true" />
      <LoadingWords
        words={[
          `Buscando cómo llegar de ${origin} a ${destination}…`,
          "Leyendo guías y blogs de viajeros…",
          "Partiendo el viaje en tramos…",
          "Viendo dónde toca hacer transbordo…",
          "Eligiendo cómo moverse en cada tramo…",
        ]}
      />
      <div className="trip-layout" aria-hidden="true">
        <div className="trip-hops">
          <SkeletonCard />
          <div className="join">
            <span className="mayu" />
          </div>
          <SkeletonCard />
        </div>
        <div className="trip-map-column">
          <div className="trip-map-frame skeleton-block" />
        </div>
      </div>
    </section>
  );
}

function SkeletonCard() {
  return (
    <div className="hop-card skeleton-card">
      <span className="skeleton-line skeleton-title" />
      <span className="skeleton-line" />
      <span className="skeleton-line skeleton-short" />
    </div>
  );
}
