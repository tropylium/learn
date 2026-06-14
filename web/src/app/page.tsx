"use client";

import { useState } from "react";

const INSTALL_CMD = "curl -LsSf https://learn-one-lac.vercel.app/install.sh | sh";
const GITHUB_URL = "https://github.com/tropylium/learn";

export default function Home() {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(INSTALL_CMD);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — user can select manually */
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center bg-black px-6 py-20 font-mono text-zinc-100">
      <div className="w-full max-w-2xl">
        <h1 className="text-5xl font-bold tracking-tight">
          learn<span className="text-emerald-400">_</span>
        </h1>
        <p className="mt-4 text-lg text-zinc-400">
          Teach yourself the terminal by reinforcing the commands you&apos;ve
          actually used. AI annotates what you run, scores your progress, and
          recalls commands semantically.
        </p>

        {/* install command */}
        <div className="mt-10">
          <div className="mb-2 text-xs uppercase tracking-widest text-zinc-500">
            install
          </div>
          <button
            onClick={copy}
            className="group flex w-full items-center justify-between gap-4 rounded-lg border border-zinc-800 bg-zinc-950 px-4 py-3 text-left transition-colors hover:border-emerald-500/50"
          >
            <code className="overflow-x-auto text-sm text-emerald-400">
              <span className="select-none text-zinc-600">$ </span>
              {INSTALL_CMD}
            </code>
            <span className="shrink-0 text-xs text-zinc-500 group-hover:text-zinc-300">
              {copied ? "copied ✓" : "copy"}
            </span>
          </button>
          <p className="mt-2 text-xs text-zinc-600">
            Installs an isolated CLI via uv and puts <code>learn</code> on your PATH.
          </p>
        </div>

        {/* the reveal */}
        <div className="mt-12 rounded-lg border border-zinc-800 bg-zinc-950 p-5 text-sm leading-relaxed">
          <div className="text-zinc-500">
            <span className="select-none text-zinc-600">$ </span>
            learn find{" "}
            <span className="text-zinc-300">
              &quot;pull a file from an old commit&quot;
            </span>
          </div>
          <div className="mt-2 text-emerald-400">
            git checkout a1b2c3d -- path/to/file
            <span className="text-zinc-600"> (91% match)</span>
          </div>
          <div className="text-zinc-500">
            Restore a single file from a previous commit
          </div>
        </div>

        <ol className="mt-10 space-y-2 text-sm text-zinc-400">
          <li>
            <span className="text-emerald-400">1.</span> Run commands. AI
            annotates intent, complexity, and skills.
          </li>
          <li>
            <span className="text-emerald-400">2.</span> Earn XP per skill —
            novelty and spaced reuse beat raw repetition.
          </li>
          <li>
            <span className="text-emerald-400">3.</span> Forgot a command? Ask in
            plain English with <code>learn find</code>.
          </li>
        </ol>

        <div className="mt-12 border-t border-zinc-900 pt-6 text-xs text-zinc-600">
          <a href={GITHUB_URL} className="hover:text-zinc-300">
            github.com/tropylium/learn
          </a>
        </div>
      </div>
    </main>
  );
}
