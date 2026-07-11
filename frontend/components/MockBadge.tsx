"use client";

import { useEffect, useState } from "react";
import { isMockMode, onMockModeChange } from "@/lib/api";

/**
 * Subtle fixed badge shown whenever the app is serving mock data
 * (forced via NEXT_PUBLIC_USE_MOCKS=1 or backend unreachable).
 */
export default function MockBadge() {
  const [active, setActive] = useState(false);

  useEffect(() => {
    setActive(isMockMode());
    return onMockModeChange(setActive);
  }, []);

  if (!active) return null;

  return (
    <div
      role="status"
      className="fixed bottom-3 left-3 z-50 rounded-full bg-watch-soft border border-watch/40 px-3 py-1 text-xs font-medium text-ink/80 shadow-card"
    >
      Demo data — backend offline
    </div>
  );
}
