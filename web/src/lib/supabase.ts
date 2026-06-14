import { createClient } from "@supabase/supabase-js";
import { env } from "./env";

// Server-side client using the service-role key. Bypasses RLS — only ever used
// from API routes, never shipped to the browser. When real auth lands, we'll
// scope queries by the authenticated user_id (and add RLS as defense in depth).
export function supabaseAdmin() {
  return createClient(env.supabaseUrl(), env.supabaseServiceKey(), {
    auth: { persistSession: false },
  });
}
