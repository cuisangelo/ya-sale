import { Suspense } from "react";
import { TripScreen } from "./trip-screen";

export default function ViajePage() {
  return (
    <Suspense fallback={<p className="shell shell-narrow loading">Armando tu viaje…</p>}>
      <TripScreen />
    </Suspense>
  );
}
