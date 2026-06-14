// Centralized env access. These are server-only — never import this from a
// client component. Missing values throw at call time with a clear message so
// the vertical slice fails loudly instead of producing confusing 500s.

function required(name: string): string {
  const v = process.env[name];
  if (!v) {
    throw new Error(
      `Missing required env var ${name}. Set it in web/.env.local (see .env.example).`,
    );
  }
  return v;
}

export const env = {
  supabaseUrl: () => required("SUPABASE_URL"),
  supabaseServiceKey: () => required("SUPABASE_SERVICE_ROLE_KEY"),
  supabaseAnonKey: () => required("SUPABASE_ANON_KEY"),
  anthropicKey: () => required("ANTHROPIC_API_KEY"),
  openaiKey: () => required("OPENAI_API_KEY"),
};

// Models / config, in one place so they're easy to tune.
export const ANNOTATION_MODEL = "claude-haiku-4-5";
export const EMBEDDING_MODEL = "text-embedding-3-small";
export const EMBEDDING_DIMS = 1536;
