import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "./supabase";

// Verify the Bearer access token on a request and return the authenticated
// user id, or null if missing/invalid. getUser(jwt) validates the token against
// Supabase Auth — we never trust a user_id sent by the client.
export async function getUserId(req: NextRequest): Promise<string | null> {
  const header = req.headers.get("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7).trim() : null;
  if (!token) return null;

  const { data, error } = await supabaseAdmin().auth.getUser(token);
  if (error || !data.user) return null;
  return data.user.id;
}

// Convenience: 401 response for unauthenticated requests.
export function unauthorized() {
  return NextResponse.json(
    { error: "not authenticated — run `learn login`" },
    { status: 401 },
  );
}
