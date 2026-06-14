// Ranking + labelling of search results by how local a command is to the user's
// current context: same directory > same project > same machine > global.

export type Scope = "cwd" | "project" | "host" | "global";

export interface RowContext {
  cwd?: string | null;
  project?: string | null;
  hostname?: string | null;
}

export interface CurrentContext {
  cwd?: string | null;
  project?: string | null;
  host?: string | null;
}

export function scopeOf(row: RowContext, ctx: CurrentContext): Scope {
  if (ctx.cwd && row.cwd === ctx.cwd) return "cwd";
  if (ctx.project && row.project === ctx.project) return "project";
  if (ctx.host && row.hostname === ctx.host) return "host";
  return "global";
}

// Added to a 0..1 similarity so local commands surface without overriding a
// clearly better match.
export const SCOPE_BOOST: Record<Scope, number> = {
  cwd: 0.3,
  project: 0.2,
  host: 0.1,
  global: 0,
};

// Strict ordering for substring search (all matches are equally "relevant").
export const SCOPE_TIER: Record<Scope, number> = {
  cwd: 0,
  project: 1,
  host: 2,
  global: 3,
};

export function currentFromParams(p: URLSearchParams): CurrentContext {
  return {
    cwd: p.get("cwd") || null,
    project: p.get("project") || null,
    host: p.get("host") || null,
  };
}
