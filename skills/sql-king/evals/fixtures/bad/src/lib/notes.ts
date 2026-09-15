"use client";
import { createClient } from "@supabase/supabase-js";

const admin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!);

export async function search(term: string, table: string) {
  const { data } = await admin
    .from(table)
    .select("*")
    .or(`body.ilike.%${term}%`);
  return data;
}
