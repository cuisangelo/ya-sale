import Link from "next/link";

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link href="/" className={inverted ? "logo logo-inverted" : "logo"}>
      <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
        <rect width="26" height="26" rx="8" fill="var(--acc)" />
        <path d="M7 17c3-8 9-8 12-3" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="19" cy="14" r="2.2" fill="#fff" />
      </svg>
      <span className="logo-word">ya sale</span>
    </Link>
  );
}
