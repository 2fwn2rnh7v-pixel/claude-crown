"use client";
import { useEffect, useMemo, useState } from "react";
import { debounce } from "../lib/debounce";

export function Search() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<string[]>([]);

  const run = useMemo(() => debounce(async (term: string) => {
    if (term.length < 3) return;
    const res = await fetch(`/api/search?q=${encodeURIComponent(term)}`, { signal: AbortSignal.timeout(8_000) });
    if (res.ok) setHits(await res.json());
  }, 300), []);

  useEffect(() => { void run(q); }, [q, run]);

  return <input value={q} onChange={(e) => setQ(e.target.value)} />;
}
