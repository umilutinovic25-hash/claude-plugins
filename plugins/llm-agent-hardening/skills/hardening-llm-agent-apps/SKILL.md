---
name: hardening-llm-agent-apps
description: Use when hardening, security-reviewing or writing security tests and evidence for an existing web app (browser + Node/TS or similar backend) that calls an LLM or runs an agent/tool loop — e.g. "secure the app before the demo", OWASP LLM/API review, prompt injection, tool-calling policy, CSP, rate limits, proving a fix with tests.
---

# Hardening LLM-Agent Web Apps

## Overview
Obvious bugs (innerHTML, CORS `*`, stack traces, `TOOLS[name]` prototype lookups, path traversal) are found by any reviewer. This skill covers the boundaries reviewers routinely **miss or declare out of scope**, and how to **prove** each control. A control without a negative test, a positive control and a before/after result does not count.

Start with `bash scripts/scan-footguns.sh <repo>` (mechanical sweep), then walk the table.

**Make it testable first:** inject the provider transport, the clock (`now`, `wait`) and the tool registry as parameters with production defaults. A hard-coded `fetch(URL)` or `Date.now()` cannot be driven by deterministic adversarial tests; the real validators, dispatch and budgets must still run in the test.

## Commonly missed boundaries

| Boundary | Miss | Required control | Proof |
|---|---|---|---|
| Cost / availability | "rate limiting is out of scope" | Per run: max model decisions, max **total** provider attempts (retries + fallbacks share one budget), max tool calls, per-call timeout **and** total deadline. Per process: max concurrent runs + accepted-per-window. Refuse **before** the provider call (503/429 + `Retry-After`). | Count calls **at the adapter**; N parallel requests → max active ≤ cap; surplus refused with 0 provider calls; slot freed after completion **and** after client disconnect; next legit request succeeds. Fake clock for windows/deadlines. |
| Config merge | `{...DEFAULTS, ...overrides}` | `undefined` override keeps default; `NaN`/`Infinity`/`0`/negative/unknown key **throws** (`count >= NaN` is always false → limit silently gone). Validate at startup. | Table test of bad values → throws. |
| Cross-site "simple" requests | Asserting `Access-Control-Allow-Origin` only | CORS blocks *reading*, not *executing*. A `text/plain`/no-body POST from any page still runs the handler and spends quota. Require `application/json` for bodies (415) **and** check `Origin` (403; same-origin in prod, explicit list in dev). Loopback servers: allowlist `Host` (DNS rebinding). Apply to WebSocket upgrades too. | Server-side outcome: 0 sessions created / 0 provider calls for foreign Origin, `text/plain`, foreign Host. A browser no-cors POST from a second local origin. |
| Timeouts | `Promise.race` | Pass an `AbortSignal` into the provider call; after deadline start no new step; never promote a late result to success. | Provider that ignores abort and answers late with a *valid* result → still not success; signal observed aborted. |
| Tool results → model | Validating only tool *args* | Validate tool **result** shape (exact keys), byte size, before it enters the next model context; never forward raw internal objects. | Tool returns extra field holding a sentinel secret → run stops, sentinel absent from every captured provider request. |
| Static serving | Traversal only | Containment check **and** never serve dot segments (`.env`, `.git`) even if the root is misconfigured to the project folder. | Temp root with `.env` canary; `/.env`, `/%2eenv`, `/.%65nv` → not 200, canary absent. |
| CSP | Header string assertion | Enforcing header (not `-Report-Only`), `script-src 'self'`, `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`, served from the **production build**, not the dev server. | Real browser, CSP not bypassed: inline + external script blocked with `securitypolicyviolation`; **control page without CSP runs the same script**; app itself has 0 violations. |
| Logs | "don't log secrets" | Closed field set (event, timestamp, app-generated correlationId, reasonCode enum, outcome, counters). Log allowed **and** denied decisions and run completion. Never body, path ids, tool names from the model, prompts, provider output, stacks. | Hostile tool name with `\n{"event":...}` → no forged record, one JSON object per line. |
| Model final output | Validating tool calls only | Schema for the final answer (exact keys, enums, text length, no control chars); every evidence reference must point to a tool result **of this run**; a claimed plan must match one the app evaluated; UI text built by the server from validated facts where possible. | Hostile `final` with unknown keys / unevaluated claim / oversize text → run not shown as success. |
| Availability bugs | Treated as code quality | `JSON.parse` outside try, unmatched routes that never respond, unhandled rejections: each is a one-request outage. | Bad JSON → 400 **and the next request still succeeds**; unknown route → 404 within a timeout. |
| Client state | "score is validated" | localStorage/URL values are untrusted forever; never sent as authority; server state wins. | Forge storage → server snapshot unchanged, request body contains only the fixed fields. |

Prompt injection: tests with a hostile **fake provider** prove *execution control*, not model robustness — say so. If no free text reaches the model, state it and test the provider boundary.

## Proof rules
1. Every control: negative test + positive control at the boundary value.
2. Isolate: when testing limit X, set the others so X is what trips (a schema 400 does not prove authorization).
3. **Before/after:** `bash scripts/baseline-compare.sh <repo> <baseline-ref> "<probe command>"` runs one probe in a throwaway worktree of the baseline and in HEAD.
4. **Mutation check:** revert one fix, confirm its test goes red.
5. Property/fuzz tests: seeded, fixed case count, and assert the generator reached **both** sides (some allowed, some refused), or the property is vacuous.
6. Sentinel secret: prove the server loaded it, then grep the build (incl. source maps and file names), responses and logs for the **value**.
7. Run the repo's own pre-push/secret scanner on **committed** state; file names like `secrets.test.ts` can trip path rules.

Code patterns (admission, guards, resolveLimits, dot-file deny, security log): see `patterns.md`.

## Common mistakes
- Dev server (Vite/HMR) used as CSP evidence.
- Disabled button or UI counter presented as a server limit.
- `npm audit fix --force`; or an empty audit presented as proof of app security.
- Tests weakened to pass after adding a content-type check — update the request, keep the assertion.
