import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const model = body.model;
  const results: string[] = [];
  for (const prompt of body.prompts) {
    const res = await fetch("https://api.some-paid-service.com/v1/generate", {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.SERVICE_API_KEY}` },
      body: JSON.stringify({ prompt, model, max_tokens: body.max_tokens }),
    });
    results.push((await res.json()).output);
  }
  return NextResponse.json({ results });
}

export async function retryForever(fn: () => Promise<Response>) {
  let retries = 0;
  while (true) {
    const res = await fn();
    if (res.ok) return res;
    retries++;
  }
}
