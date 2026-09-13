#!/usr/bin/env bash
# Test: session-start emits valid JSON whose additionalContext carries the router text.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"

out="$(CLAUDE_PLUGIN_ROOT="$ROOT" bash "${HERE}/session-start")"

printf '%s' "$out" | node -e '
  const raw = require("fs").readFileSync(0, "utf8");
  const j = JSON.parse(raw);
  const ctx = j.hookSpecificOutput && j.hookSpecificOutput.additionalContext;
  if (j.hookSpecificOutput.hookEventName !== "SessionStart") { console.error("FAIL: hookEventName"); process.exit(1); }
  if (!ctx || !ctx.startsWith("<EXTREMELY_IMPORTANT>\nYou have Claude Crown.")) { console.error("FAIL: context prefix"); process.exit(1); }
  if (!ctx.includes("Claude Crown is a personal skill library.")) { console.error("FAIL: router body missing"); process.exit(1); }
  if (!ctx.trimEnd().endsWith("</EXTREMELY_IMPORTANT>")) { console.error("FAIL: context suffix"); process.exit(1); }
  console.log("PASS: session-start JSON ok, " + ctx.length + " chars");
'
