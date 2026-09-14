import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getUser } from "@/lib/auth";
import { checkLimit } from "@/lib/limit";

const Body = z.object({ prompt: z.string().min(1).max(2000), tier: z.enum(["fast", "precise"]).default("fast") });
const TIERS = { fast: { model: "small", maxTokens: 300 }, precise: { model: "large", maxTokens: 1200 } } as const;

export async function POST(req: NextRequest) {
  const user = await getUser(req);
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const parsed = Body.safeParse(await req.json());
  if (!parsed.success) return NextResponse.json({ error: "invalid_body" }, { status: 400 });

  const gate = await checkLimit(`u:${user.id}`);
  if (!gate.ok) return NextResponse.json({ error: "rate_limited" }, { status: 429, headers: { "Retry-After": String(gate.retryAfter) } });

  const tier = TIERS[parsed.data.tier];
  const upstream = await fetch("https://api.some-paid-service.com/v1/generate", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.SERVICE_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: parsed.data.prompt, model: tier.model, max_tokens: tier.maxTokens }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!upstream.ok) return NextResponse.json({ error: "upstream_failed" }, { status: 502 });
  return NextResponse.json({ result: (await upstream.json()).output }, { headers: { "Cache-Control": "private, no-store" } });
}
