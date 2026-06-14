import { NextRequest, NextResponse } from "next/server";
import { supabaseAnon } from "@/lib/supabase";

export const runtime = "nodejs";

// Step 1 of email-OTP login: send a one-time code to the user's email.
// Requires the Supabase email template to emit {{ .Token }} (a 6-digit code)
// rather than a magic link.
export async function POST(req: NextRequest) {
  let email: string | undefined;
  try {
    ({ email } = await req.json());
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  if (!email?.trim()) {
    return NextResponse.json({ error: "email required" }, { status: 400 });
  }

  const { error } = await supabaseAnon().auth.signInWithOtp({
    email: email.trim(),
    options: { shouldCreateUser: true },
  });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}
