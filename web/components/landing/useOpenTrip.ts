"use client";

import { useRouter } from "next/navigation";
import { limaToday, tripHref } from "../../lib/landing";

export function useOpenTrip(): (origin: string, destination: string) => void {
  const router = useRouter();
  return (origin, destination) => {
    const today = limaToday(new Date());
    const result = tripHref({ origin, destination, date: today }, today);
    if (!result.ok) throw new Error(`Invalid example trip: ${result.error}`);
    router.push(result.href);
  };
}
