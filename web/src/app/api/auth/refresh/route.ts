import { NextRequest, NextResponse } from "next/server";
import { supabaseAnon } from "@/lib/supabase";

export const runtime = "nodejs";

// Exchange a refresh token for a fresh session. The CLI calls this on a 401 so
// short-lived access tokens don't interrupt a session.
export async function POST(req: NextRequest) {
  let refresh_token: string | undefined;
  try {
    ({ refresh_token } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!refresh_token) {
    return NextResponse.json({ error: "refresh_token required" }, { status: 400 });
  }

  const { data, error } = await supabaseAnon().auth.refreshSession({ refresh_token });
  if (error || !data.session) {
    return NextResponse.json(
      { error: error?.message ?? "could not refresh session" },
      { status: 401 },
    );
  }

  return NextResponse.json({
    access_token: data.session.access_token,
    refresh_token: data.session.refresh_token,
    expires_at: data.session.expires_at,
  });
}
