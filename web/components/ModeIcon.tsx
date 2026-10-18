import { modeIconSrc } from "../lib/format";

export function ModeIcon({ mode }: { mode: string }) {
  const src = modeIconSrc(mode);
  return <span className="mode-icon">{src ? <img src={src} alt="" width={22} height={22} /> : null}</span>;
}
