import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { annotateCommand, embed } from "@/lib/annotate";
import { computePoints } from "@/lib/scoring";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";
export const maxDuration = 30;

interface LogBody {
  command: string;
  exit_code?: number;
  hostname?: string;
  project?: string;
  cwd?: string;
}

export async function POST(req: NextRequest) {
  const user_id = await getUserId(req);
  if (!user_id) return unauthorized();

  let body: LogBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }
  const { command } = body;
  if (!command?.trim()) {
    return NextResponse.json({ error: "command required" }, { status: 400 });
  }

  const db = supabaseAdmin();

  // Is this command already known for this user? (exact-string match for v1;
  // argument-normalized keys are a documented future improvement.)
  const { data: existing, error: selErr } = await db
    .from("commands")
    .select("id, complexity, skills, intent")
    .eq("user_id", user_id)
    .eq("command", command)
    .maybeSingle();
  if (selErr) {
    return NextResponse.json({ error: selErr.message }, { status: 500 });
  }

  let commandId: string;
  let complexity: number;
  let intent: string;
  let skills: string[];

  if (existing) {
    commandId = existing.id;
    complexity = existing.complexity ?? 1;
    intent = existing.intent ?? "";
    skills = existing.skills ?? [];
  } else {
    // New command for this user: annotate + embed, then store.
    const annotation = await annotateCommand(command);
    const intentForEmbedding = `${annotation.intent}\n${command}`;
    const embedding = await embed(intentForEmbedding);

    const { data: inserted, error: insErr } = await db
      .from("commands")
      .insert({
        user_id,
        command,
        intent: annotation.intent,
        explanation: annotation.explanation,
        complexity: annotation.complexity,
        skills: annotation.skills,
        embedding,
        hostname: body.hostname,
        project: body.project,
        cwd: body.cwd,
      })
      .select("id")
      .single();
    if (insErr) {
      return NextResponse.json({ error: insErr.message }, { status: 500 });
    }
    commandId = inserted.id;
    complexity = annotation.complexity;
    intent = annotation.intent;
    skills = annotation.skills;
  }

  // Count prior uses and find the most recent use, for scoring.
  const { count: priorUses } = await db
    .from("command_uses")
    .select("id", { count: "exact", head: true })
    .eq("command_id", commandId);

  const { data: lastUse } = await db
    .from("command_uses")
    .select("used_at")
    .eq("command_id", commandId)
    .order("used_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const hoursSinceLast = lastUse
    ? (Date.now() - new Date(lastUse.used_at).getTime()) / 3_600_000
    : null;

  const points = computePoints(complexity, priorUses ?? 0, hoursSinceLast);

  const { error: useErr } = await db.from("command_uses").insert({
    command_id: commandId,
    user_id,
    exit_code: body.exit_code ?? 0,
    points_awarded: points,
  });
  if (useErr) {
    return NextResponse.json({ error: useErr.message }, { status: 500 });
  }

  return NextResponse.json({
    intent,
    skills,
    complexity,
    points_awarded: points,
    is_new: !existing,
  });
}
