"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export const LogoutButton = () => {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const logout = async () => {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
      router.refresh();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <button
      type="button"
      onClick={logout}
      disabled={isLoggingOut}
      className="rounded-full border border-[var(--stroke)] bg-white/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)] shadow-[var(--shadow)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] disabled:cursor-not-allowed disabled:opacity-70"
    >
      {isLoggingOut ? "Signing out..." : "Log out"}
    </button>
  );
};
