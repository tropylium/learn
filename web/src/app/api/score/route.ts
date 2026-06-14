import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";

// XP per skill + total — powers `learn score` and the dashboard XP bars.
export async function GET(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  const db = supabaseAdmin();
  const { data, error } = await db.rpc("skill_scores", { p_user_id: user_id });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const skills = (data ?? []).map((r: { skill: string; xp: number }) => ({
    skill: r.skill,
    xp: Math.round(Number(r.xp) * 10) / 10,
  }));
  const total =
    Math.round(skills.reduce((s: number, r: { xp: number }) => s + r.xp, 0) * 10) / 10;

  return NextResponse.json({ total_xp: total, skills });
}
