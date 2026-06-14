import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { ANNOTATION_MODEL, EMBEDDING_MODEL, env } from "./env";

export interface Annotation {
  intent: string; // "Restore a file from a previous commit"
  explanation: string; // one or two sentences
  complexity: number; // 1-5
  skills: string[]; // e.g. ["git", "history-surgery"]
}

// JSON schema for structured output — guarantees we get parseable fields back
// from Haiku instead of having to coax JSON out of free text.
const ANNOTATION_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    intent: {
      type: "string",
      description:
        "What the user was trying to DO, phrased as a goal in plain English. E.g. 'Recursively search Python files for a pattern with line numbers'.",
    },
    explanation: {
      type: "string",
      description: "One or two sentences explaining what the command does and any notable flags.",
    },
    complexity: {
      type: "integer",
      description:
        "How advanced this command is, 1 (trivial, e.g. `ls`) to 5 (expert, many flags / piped / obscure).",
      enum: [1, 2, 3, 4, 5],
    },
    skills: {
      type: "array",
      description:
        "1-3 lowercase skill tags clustering this command, e.g. ['git'], ['text-processing'], ['slurm'].",
      items: { type: "string" },
    },
  },
  required: ["intent", "explanation", "complexity", "skills"],
} as const;

const SYSTEM = `You annotate shell commands to help a developer learn the terminal.
Given one command, infer what the user was trying to accomplish and rate it.
Be concise. The "intent" is the unit of learning — describe the goal, not the syntax.
Skill tags should be reusable clusters (e.g. 'git', 'text-processing', 'process-inspection'), not argument-specific.`;

export async function annotateCommand(command: string): Promise<Annotation> {
  const client = new Anthropic({ apiKey: env.anthropicKey() });

  const response = await client.messages.create({
    model: ANNOTATION_MODEL,
    max_tokens: 1024,
    system: SYSTEM,
    output_config: { format: { type: "json_schema", schema: ANNOTATION_SCHEMA } },
    messages: [{ role: "user", content: `Command:\n${command}` }],
  });

  const textBlock = response.content.find((b) => b.type === "text");
  if (!textBlock || textBlock.type !== "text") {
    throw new Error("annotation returned no text content");
  }
  const parsed = JSON.parse(textBlock.text) as Annotation;
  // Clamp/normalize defensively.
  parsed.complexity = Math.min(5, Math.max(1, Math.round(parsed.complexity || 1)));
  parsed.skills = (parsed.skills || []).map((s) => s.toLowerCase().trim()).filter(Boolean);
  return parsed;
}

export async function embed(text: string): Promise<number[]> {
  const client = new OpenAI({ apiKey: env.openaiKey() });
  const res = await client.embeddings.create({ model: EMBEDDING_MODEL, input: text });
  return res.data[0].embedding;
}

// Per-token breakdown for `learn practice`. Given a command and its tokens (the
// CLI's own tokenization, so alignment is exact), return one short explanation
// per token, in the same order. Used to reveal explanations as the user types.
export async function explainTokens(
  command: string,
  tokens: string[],
): Promise<string[]> {
  const client = new Anthropic({ apiKey: env.anthropicKey() });

  const schema = {
    type: "object",
    additionalProperties: false,
    properties: {
      parts: {
        type: "array",
        description:
          "One short (max ~10 words) explanation per input token, in the SAME order and SAME count as the provided tokens. Explain what each program/subcommand/flag/argument does in this command.",
        items: { type: "string" },
      },
    },
    required: ["parts"],
  } as const;

  const response = await client.messages.create({
    model: ANNOTATION_MODEL,
    max_tokens: 1024,
    system:
      "You explain shell commands part by part to help a developer learn. " +
      "Return exactly one concise explanation per token, same order, same count.",
    output_config: { format: { type: "json_schema", schema } },
    messages: [
      {
        role: "user",
        content: `Command:\n${command}\n\nTokens (explain each, in order):\n${JSON.stringify(tokens)}`,
      },
    ],
  });

  const textBlock = response.content.find((b) => b.type === "text");
  if (!textBlock || textBlock.type !== "text") {
    throw new Error("explain returned no text content");
  }
  const parsed = JSON.parse(textBlock.text) as { parts: string[] };
  const parts = parsed.parts ?? [];
  // Normalize length to match tokens exactly.
  if (parts.length < tokens.length) {
    return [...parts, ...Array(tokens.length - parts.length).fill("")];
  }
  return parts.slice(0, tokens.length);
}
