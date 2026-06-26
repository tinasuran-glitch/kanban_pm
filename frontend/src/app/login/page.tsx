"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type LoginState = {
  username: string;
  password: string;
};

const initialState: LoginState = {
  username: "",
  password: "",
};

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState<LoginState>(initialState);
  const [error, setError] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        setError(payload?.detail ?? "Unable to sign in.");
        return;
      }

      router.replace("/");
      router.refresh();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden px-6 py-12">
      <div className="pointer-events-none absolute left-0 top-0 h-[360px] w-[360px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.22)_0%,_rgba(32,157,215,0.05)_55%,_transparent_72%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[430px] w-[430px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.2)_0%,_rgba(117,57,145,0.05)_55%,_transparent_72%)]" />

      <section className="relative w-full max-w-md rounded-3xl border border-[var(--stroke)] bg-white/90 p-8 shadow-[var(--shadow)] backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--gray-text)]">
          Project Management MVP
        </p>
        <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
          Sign in
        </h1>
        <p className="mt-2 text-sm text-[var(--gray-text)]">
          Use the MVP credentials to access your board.
        </p>

        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--gray-text)]">
              Username
            </span>
            <input
              name="username"
              value={form.username}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, username: event.target.value }))
              }
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              autoComplete="username"
              required
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--gray-text)]">
              Password
            </span>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, password: event.target.value }))
              }
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              autoComplete="current-password"
              required
            />
          </label>

          {error ? (
            <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
