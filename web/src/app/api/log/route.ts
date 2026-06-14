import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabase";
import { annotateCommand, embed } from "@/lib/annotate";
import { getUserId, unauthorized } from "@/lib/auth";

export const runtime = "nodejs";
export const maxDuration = 30;

interface LogBody {
  command: string;
  signature?: string; // normalized program+subcommand+flags; computed by the CLI
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
  // Fall back to the raw command if the client didn't send a signature.
  const signature = body.signature?.trim() || command.trim();

  const db = supabaseAdmin();

  // Group by signature: `git commit -m "a"` and `git commit -m "b"` are one
  // thing used twice. The stored `command` is the most recent literal form.
  const { data: existing, error: selErr } = await db
    .from("commands")
    .select("id, skills, intent")
    .eq("user_id", user_id)
    .eq("signature", signature)
    .maybeSingle();
  if (selErr) {
    return NextResponse.json({ error: selErr.message }, { status: 500 });
  }

  let commandId: string;
  let intent: string;
  let skills: string[];

  if (existing) {
    commandId = existing.id;
    intent = existing.intent ?? "";
    skills = existing.skills ?? [];
    // Refresh the displayed literal command to the latest invocation.
    await db.from("commands").update({ command }).eq("id", commandId);
  } else {
    // New signature for this user: annotate + embed once, then store.
    const annotation = await annotateCommand(command);
    const embedding = await embed(`${annotation.intent}\n${command}`);

    const { data: inserted, error: insErr } = await db
      .from("commands")
      .insert({
        user_id,
        command,
        signature,
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
    intent = annotation.intent;
    skills = annotation.skills;
  }

  // Record this use (simple count-based model — no scoring weights).
  const { error: useErr } = await db.from("command_uses").insert({
    command_id: commandId,
    user_id,
    exit_code: body.exit_code ?? 0,
  });
  if (useErr) {
    return NextResponse.json({ error: useErr.message }, { status: 500 });
  }

  const { count: timesUsed } = await db
    .from("command_uses")
    .select("id", { count: "exact", head: true })
    .eq("command_id", commandId);

  return NextResponse.json({
    intent,
    skills,
    times_used: timesUsed ?? 1,
    is_new: !existing,
  });
}
