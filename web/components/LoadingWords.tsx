import { useEffect, useState } from "react";

const STEP_SECONDS = 3;
const STILL_WORKING = "Seguimos en eso: algunas páginas tardan en responder…";

// The server emits no sub-steps, so the phrases follow the steps it is known to run in order and
// then hold on STILL_WORKING; the ticking seconds are the real proof the request is alive.
export function LoadingWords({ words }: { words: string[] }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = window.setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, []);

  const phrases = [...words, STILL_WORKING];
  const step = Math.min(Math.floor(seconds / STEP_SECONDS), phrases.length - 1);

  return (
    <p className="loading-words">
      <span className="loading-spinner" aria-hidden="true" />
      <span key={step} className="loading-word">
        {phrases[step]}
      </span>
      {seconds > 0 ? <span className="mono loading-elapsed">{seconds} s</span> : null}
    </p>
  );
}
