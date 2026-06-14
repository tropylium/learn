"use client";

import { useState } from "react";

const INSTALL_CMD = "curl -LsSf https://learn-one-lac.vercel.app/install.sh | sh";
const GITHUB_URL = "https://github.com/tropylium/learn";

interface Cmd {
  name: string;
  usage: string;
  desc: string;
}

const COMMANDS: Cmd[] = [
  {
    name: "login",
    usage: "learn login",
    desc: "Sign in with a one-time code emailed to you. Tokens are stored locally and refreshed automatically.",
  },
  {
    name: "new",
    usage: 'learn new "<goal>"',
    desc: "Describe what you want to do in plain English; pick from suggested commands, then practice the one you choose. Picked commands are saved to your history.",
  },
  {
    name: "log",
    usage: "learn log [cmd]",
    desc: "Log a command — it's annotated (intent, skills) and stored. With no argument it logs your last shell command; -n 5 logs the last 5. Or pass a command explicitly.",
  },
  {
    name: "find",
    usage: "learn find",
    desc: "Interactively search your history — substring matches as you type, then semantic matches. Results are ranked and colored by context (here / project / machine / elsewhere). Enter copies, Tab practices, Esc cancels.",
  },
  {
    name: "practice",
    usage: 'learn practice "<cmd>"',
    desc: "Reconstruct a command from a guided template, learning each part as you type — flags can be in any order and argument values are free.",
  },
  {
    name: "here",
    usage: "learn here",
    desc: "Show the commands you've logged in the current project.",
  },
  {
    name: "shell-init",
    usage: 'eval "$(learn shell-init)"',
    desc: "Shell integration so `learn log` can capture the current session's last command. The installer adds this to your shell rc automatically.",
  },
  {
    name: "whoami / logout",
    usage: "learn whoami",
    desc: "Show or clear the signed-in account.",
  },
  {
    name: "config",
    usage: "learn config --api-url <url>",
    desc: "View or set local config, such as the API URL the CLI talks to.",
  },
  {
    name: "uninstall",
    usage: "learn uninstall",
    desc: "Remove learn: shell integration, local config, and the installed CLI.",
  },
];

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
    <main className="flex flex-1 flex-col items-center bg-white px-6 py-20 font-mono text-zinc-900">
      <div className="w-full max-w-2xl">
        <h1 className="text-5xl font-bold tracking-tight">
          learn<span className="text-emerald-600">_</span>
        </h1>
        <p className="mt-4 text-lg text-zinc-600">
          Teach yourself the terminal by reinforcing the commands you&apos;ve
          actually used. AI annotates what you run and recalls commands
          semantically — so you learn them instead of looking them up forever.
        </p>

        {/* install command */}
        <div className="mt-10">
          <div className="mb-2 text-xs uppercase tracking-widest text-zinc-400">
            install
          </div>
          <button
            onClick={copy}
            className="group flex w-full items-center justify-between gap-4 rounded-lg border border-zinc-300 bg-zinc-50 px-4 py-3 text-left transition-colors hover:border-emerald-500"
          >
            <code className="overflow-x-auto text-sm text-emerald-700">
              <span className="select-none text-zinc-400">$ </span>
              {INSTALL_CMD}
            </code>
            <span className="shrink-0 text-xs text-zinc-400 group-hover:text-zinc-700">
              {copied ? "copied ✓" : "copy"}
            </span>
          </button>
          <p className="mt-2 text-xs text-zinc-400">
            Installs an isolated CLI via uv and puts <code>learn</code> on your PATH.
          </p>
        </div>

        {/* the reveal */}
        <div className="mt-12 rounded-lg border border-zinc-200 bg-zinc-50 p-5 text-sm leading-relaxed">
          <div className="text-zinc-500">
            <span className="select-none text-zinc-400">$ </span>
            learn find{" "}
            <span className="text-zinc-700">
              &quot;pull a file from an old commit&quot;
            </span>
          </div>
          <div className="mt-2 text-emerald-700">
            git checkout a1b2c3d -- path/to/file
            <span className="text-zinc-400"> (91% match)</span>
          </div>
          <div className="text-zinc-500">
            Restore a single file from a previous commit
          </div>
        </div>

        <ol className="mt-10 space-y-2 text-sm text-zinc-600">
          <li>
            <span className="text-emerald-600">1.</span> Run commands — AI
            annotates each one&apos;s intent and skills.
          </li>
          <li>
            <span className="text-emerald-600">2.</span> Forgot one? Ask in plain
            English with <code>learn find</code>, scoped to where you are.
          </li>
          <li>
            <span className="text-emerald-600">3.</span> Learn a new one with{" "}
            <code>learn new</code> — suggestions you practice by hand.
          </li>
        </ol>

        {/* command documentation */}
        <h2 className="mt-16 text-xs uppercase tracking-widest text-zinc-400">
          commands
        </h2>
        <dl className="mt-4 divide-y divide-zinc-200 border-t border-zinc-200">
          {COMMANDS.map((c) => (
            <div key={c.name} className="py-4">
              <dt>
                <code className="rounded bg-zinc-100 px-2 py-1 text-sm text-emerald-700">
                  {c.usage}
                </code>
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-zinc-600">
                {c.desc}
              </dd>
            </div>
          ))}
        </dl>

        <div className="mt-12 border-t border-zinc-200 pt-6 text-xs text-zinc-400">
          <a href={GITHUB_URL} className="hover:text-zinc-700">
            github.com/tropylium/learn
          </a>
        </div>
      </div>
    </main>
  );
}
