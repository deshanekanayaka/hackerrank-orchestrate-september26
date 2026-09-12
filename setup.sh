#!/usr/bin/env bash
# setup.sh — run once, after the hackathon material is in this directory.
#
# Safe to run more than once. It never overwrites hackathon files.

set -uo pipefail

say()  { printf '  %s\n' "$1"; }
ok()   { printf '  [ok]   %s\n' "$1"; }
warn() { printf '  [warn] %s\n' "$1"; }
head_() { printf '\n%s\n' "$1"; }

printf '\n=== Orchestrate starter setup ===\n'

# ---------------------------------------------------------------- 1. sanity
head_ '1. Checking the hackathon material landed'

FOUND_PROBLEM=0
for f in problem_statement.md PROBLEM_STATEMENT.md problem-statement.md; do
  [ -f "$f" ] && { ok "found $f"; FOUND_PROBLEM=1; break; }
done
[ "$FOUND_PROBLEM" -eq 0 ] && warn "no problem statement found - is the hackathon material in this directory?"

[ -d dataset ]  && ok "found dataset/"  || warn "no dataset/ directory (may be named differently this edition)"
[ -d code ]     && ok "found code/"     || say  "no code/ directory - will create one"
[ -f AGENTS.md ] && ok "found AGENTS.md" || warn "no AGENTS.md - transcript logging may not be configured"

[ -d code ] || { mkdir -p code && ok "created code/"; }

# ---------------------------------------------------------- 2. merge CLAUDE.md
head_ '2. Merging the operating agreement into CLAUDE.md'

MARKER='<!-- orchestrate-starter:begin -->'

if [ ! -f CLAUDE.orchestrate.md ]; then
  warn "CLAUDE.orchestrate.md missing - skipping merge"
elif [ -f CLAUDE.md ] && grep -qF "$MARKER" CLAUDE.md; then
  ok "already merged, leaving CLAUDE.md alone"
else
  {
    printf '\n\n%s\n' "$MARKER"
    cat CLAUDE.orchestrate.md
    printf '\n<!-- orchestrate-starter:end -->\n'
  } >> CLAUDE.md
  if [ -s CLAUDE.md ]; then
    ok "appended operating agreement to CLAUDE.md"
    say "open CLAUDE.md and skim for conflicts with the platform's rules"
  fi
fi

# --------------------------------------------------------------- 3. secrets
head_ '3. Environment and secrets'

if [ -f .env ]; then
  ok ".env already exists, not touching it"
else
  printf 'ANTHROPIC_API_KEY=\n' > .env
  ok "created .env - paste your key into it now"
fi

touch .gitignore
for entry in .env cache/ __pycache__/ node_modules/ .DS_Store; do
  grep -qxF "$entry" .gitignore || printf '%s\n' "$entry" >> .gitignore
done
ok "ignore list updated"

mkdir -p cache && ok "created cache/ for derived data"

# ------------------------------------------------------------------ 4. docs
head_ '4. Starter docs'

mkdir -p docs
[ -f tasks.md ]     && ok "tasks.md in place"     || warn "tasks.md missing from the starter"
[ -f PROMPTS.md ]   && ok "PROMPTS.md in place"   || warn "PROMPTS.md missing from the starter"
[ -f DOCS-SPEC.md ] && ok "DOCS-SPEC.md in place" || warn "DOCS-SPEC.md missing from the starter"

# ------------------------------------------------------------------- 5. git
head_ '5. Version control'

if [ -d .git ]; then
  ok "git repo already initialised"
else
  git init -q 2>/dev/null && ok "git initialised" || warn "git init failed - not fatal"
fi

# ------------------------------------------------------------------ 6. clock
head_ '6. Clock times'

if grep -q '{{clock time}}' tasks.md 2>/dev/null; then
  printf '  Enter H0 start time (e.g. 09:00), or press enter to skip: '
  read -r H0
  if [ -n "${H0:-}" ]; then
    tmp=$(mktemp)
    sed -e "s|^\*\*H0\*\*: {{clock time}}|**H0**: $H0|" \
        -e "s|^\*\*H24\*\*: {{clock time}}|**H24**: $H0 (next day)|" \
        tasks.md > "$tmp" && mv "$tmp" tasks.md
    ok "H0 $H0, H24 $H0 next day"
    say "check that against the real deadline - editions vary"
  else
    say "skipped - fill the clock times in tasks.md yourself"
  fi
else
  ok "clock times already set"
fi

# ------------------------------------------------------------------- done
cat <<'DONE'

=== Setup complete ===

Next:
  1. Paste your API key into .env
  2. Skim CLAUDE.md for conflicts between the platform rules and the starter rules
  3. Open this folder in VS Code:   code .
  4. Split the terminal, run:       claude
  5. Verify the skills:             /ponytail        (should report "full")
  6. Paste the H0-H2 prompt from PROMPTS.md and begin

DONE
