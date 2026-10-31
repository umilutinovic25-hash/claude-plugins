#!/usr/bin/env bash
# Mechanical sweep for LLM-agent web app footguns. Hits are leads, not findings: read each one.
# Usage: bash scan-footguns.sh <repo-dir>
set -u
ROOT="${1:-.}"
cd "$ROOT" || exit 2
GLOB=(--include='*.ts' --include='*.tsx' --include='*.js' --include='*.mjs' --include='*.jsx' --include='*.html' --include='*.vue' --include='*.svelte')
EXCL=(--exclude='*.test.*' --exclude='*.spec.*' --exclude='*.e2e.*' --exclude-dir=tests --exclude-dir=__tests__ --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build --exclude-dir=.git --exclude-dir=coverage)
hits=0
check() {
  local title="$1" pattern="$2"
  local out
  out=$(grep -rnE "${GLOB[@]}" "${EXCL[@]}" -e "$pattern" . 2>/dev/null | head -20)
  if [ -n "$out" ]; then echo "== $title"; echo "$out"; echo; hits=$((hits + 1)); fi
}
check "DOM sinks (XSS)" 'innerHTML|outerHTML|insertAdjacentHTML|dangerouslySetInnerHTML|document\.write|srcdoc|v-html|\{@html'
check "Dynamic code" '\beval\(|new Function\('
check "CSP report-only (does not block)" '[Cc]ontent-[Ss]ecurity-[Pp]olicy-[Rr]eport-[Oo]nly'
check "Wildcard CORS" '[Aa]ccess-[Cc]ontrol-[Aa]llow-[Oo]rigin.{0,6}\*'
check "Limit/config spread (undefined/NaN overrides disable limits)" '\{ *\.\.\.[A-Z_]*(DEFAULT|LIMIT|CONFIG)[A-Z_]*, *\.\.\.'
check "Promise.race timeout (does it abort the underlying work?)" 'Promise\.race'
check "Dynamic registry/tool lookup (prototype keys)" '(TOOLS|tools|registry|handlers)\[[a-zA-Z_.]+\]'
check "Stack traces / raw errors in responses" '\.stack\b|String\(err|String\(error'
check "Logging raw bodies/prompts/provider output" 'console\.(log|info|warn|error)\(.*(body|raw|prompt|response|payload)'
check "Client-exposed env secrets" 'VITE_[A-Z_]*(KEY|SECRET|TOKEN)|NEXT_PUBLIC_[A-Z_]*(KEY|SECRET|TOKEN)|import\.meta\.env\.[A-Z_]*(KEY|SECRET|TOKEN)'
check "Unbounded JSON.parse on request text" 'JSON\.parse\((raw|body|text|data)\)'
check "Static file serving (check containment + dot files)" 'readFile\(|createReadStream\(|sendFile\(|express\.static'
check "Client storage used as data source (untrusted)" 'localStorage\.(getItem|setItem)|sessionStorage\.'
echo "scan-footguns: $hits categories with leads in $ROOT"
