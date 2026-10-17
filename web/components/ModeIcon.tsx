import { modeIconSrc, modeTone } from "../lib/format";

export function ModeIcon({ mode }: { mode: string }) {
  const src = modeIconSrc(mode);
  return (
    <span className={`mode-icon tone-${modeTone(mode)}`}>
      {src ? <img src={src} alt="" width={22} height={22} /> : null}
    </span>
  );
}
