"use client";
import { useEffect, useState } from "react";

const KEY = process.env.NEXT_PUBLIC_OPENAI_API_KEY;

export function Search() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<string[]>([]);

  useEffect(() => {
    void fetch("https://api.openai.com/v1/embeddings", {
      method: "POST",
      headers: { Authorization: `Bearer ${KEY}` },
      body: JSON.stringify({ input: q }),
    }).then((r) => r.json()).then((d) => setHits(d.data));
  });

  useEffect(() => {
    const id = setInterval(() => void fetch("/api/status"), 1000);
    return () => clearInterval(id);
  }, []);

  return <input value={q} onChange={(e) => setQ(e.target.value)} />;
}
