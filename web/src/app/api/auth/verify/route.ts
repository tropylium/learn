import { NextRequest, NextResponse } from "next/server";
import { supabaseAnon } from "@/lib/supabase";

export const runtime = "nodejs";

// Step 2 of email-OTP login: exchange the emailed code for a session. Returns
// the tokens the CLI stores in ~/.config/learn/auth.json.
export async function POST(req: NextRequest) {
  let email: string | undefined;
  let token: string | undefined;
  try {
    ({ email, token } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!email?.trim() || !token?.trim()) {
    return NextResponse.json({ error: "email and token required" }, { status: 400 });
  }

  const { data, error } = await supabaseAnon().auth.verifyOtp({
    email: email.trim(),
    token: token.trim(),
    type: "email",
  });
  if (error || !data.session || !data.user) {
    return NextResponse.json(
      { error: error?.message ?? "invalid or expired code" },
      { status: 401 },
    );
  }

  return NextResponse.json({
    access_token: data.session.access_token,
    refresh_token: data.session.refresh_token,
    expires_at: data.session.expires_at,
    user_id: data.user.id,
    email: data.user.email,
  });
}
