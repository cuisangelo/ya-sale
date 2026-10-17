import Link from "next/link";

export function Logo({ size = 46, compact = false }: { size?: number; compact?: boolean }) {
  return (
    <Link href="/" className={compact ? "logo logo-compact" : "logo"}>
      <img src="/textil/logo-inti.svg" width={size} height={size} alt="" />
      <span className="logo-word">Ya Sale</span>
    </Link>
  );
}
