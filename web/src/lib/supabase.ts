import { createClient } from "@supabase/supabase-js";
import { env } from "./env";

// Server-side client using the service-role key. Bypasses RLS — only ever used
// from API routes, never shipped to the browser. Every query is scoped by the
// JWT-verified user_id (see lib/auth), and RLS exists as defense in depth.
export function supabaseAdmin() {
  return createClient(env.supabaseUrl(), env.supabaseServiceKey(), {
    auth: { persistSession: false },
  });
}

// Anon-key client for auth operations (OTP send/verify/refresh). The anon key
// is safe to use server-side here; it has no elevated privileges.
export function supabaseAnon() {
  return createClient(env.supabaseUrl(), env.supabaseAnonKey(), {
    auth: { persistSession: false },
  });
}
