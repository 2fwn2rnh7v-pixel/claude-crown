import { createClient } from "./supabase/client";

export async function listNotes(term: string) {
  const supabase = createClient();
  const safe = term.replace(/[,()\.*]/g, "");
  const { data, error } = await supabase
    .from("notes")
    .select("id, body, created_at")
    .ilike("body", `%${safe}%`)
    .order("created_at", { ascending: false })
    .limit(50);
  if (error) throw new Error(`Loading notes failed: ${error.message}`);
  return data;
}
