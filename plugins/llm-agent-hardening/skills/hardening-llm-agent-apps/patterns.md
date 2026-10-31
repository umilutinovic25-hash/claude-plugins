# Patterns (TypeScript / Node http)

## resolveLimits — fail closed on bad config
```ts
export function resolveLimits<T extends Record<string, number>>(defaults: T, overrides: Partial<Record<keyof T, unknown>> = {}): T {
  const merged: Record<string, number> = { ...defaults };
  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined) continue;                       // spread would replace the default
    if (!Object.hasOwn(defaults, key)) throw new Error(`Unknown limit: ${key}`);
    merged[key] = value as number;
  }
  for (const [key, value] of Object.entries(merged))
    if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(`Limit ${key} must be a positive integer.`);
  return merged as T;
}
```

## Admission control (one process; global when there is no identity)
```ts
export function createAdmissionControl({ maxConcurrent = 2, maxPerWindow = 5, windowMs = 60_000 } = {}, now = Date.now) {
  let active = 0; let accepted: number[] = [];
  return {
    get active() { return active; },
    tryAcquire() {
      const t = now(); accepted = accepted.filter((x) => t - x < windowMs);
      if (active >= maxConcurrent) return { ok: false as const, reason: "CAPACITY_EXCEEDED", retryAfterSeconds: 1 };
      if (accepted.length >= maxPerWindow) return { ok: false as const, reason: "RATE_LIMITED", retryAfterSeconds: Math.max(1, Math.ceil((accepted[0] + windowMs - t) / 1000)) };
      active += 1; accepted.push(t); let done = false;
      return { ok: true as const, release() { if (!done) { done = true; active -= 1; } } };
    },
  };
}
// Route: validate body + resource state FIRST (cheap, no budget used), then tryAcquire, then try/finally release().
```

## Request guards
```ts
const LOOPBACK = new Set(["localhost", "127.0.0.1", "[::1]"]);
const host = (v: string) => { try { return new URL(v.includes("://") ? v : `http://${v}`).hostname.toLowerCase(); } catch { return null; } };
export const allowedHost = (req) => LOOPBACK.has(host(req.headers.host ?? "") ?? "");          // DNS rebinding
export function allowedOrigin(req, extra: string[] = [], sameOriginOnly = false) {
  const o = req.headers.origin; if (o === undefined) return true;                               // non-browser client
  if (extra.includes(o)) return true;                                                            // validate extra: exact http(s) origins, never "*" or "null"
  return sameOriginOnly ? o === `http://${req.headers.host}` : LOOPBACK.has(host(o) ?? "");
}
// Body: reject Content-Length > cap before reading; count bytes while streaming; non-empty body must be application/json (415).
```

## Static files
```ts
const rel = decodeURIComponent(urlPath);
if (rel.includes("\0") || rel.split(/[\\/]/).some((s) => s.startsWith("."))) return notFound();   // .env, .git
const file = normalize(join(base, rel === "/" ? "/index.html" : rel));
if (file !== base && !file.startsWith(base + sep)) return notFound();
// headers: content-security-policy (enforcing), x-content-type-options: nosniff, referrer-policy: no-referrer
```

## Security log
```ts
// Build the event from a closed set of fields; never spread caller/model objects into it.
write(JSON.stringify({ event, timestamp: new Date().toISOString(), correlationId, reasonCode, outcome, ...(status !== undefined ? { status } : {}) }));
```

## Browser CSP proof (Playwright)
```ts
await page.addInitScript(() => { window.__v = []; document.addEventListener("securitypolicyviolation", (e) => window.__v.push(`${e.effectiveDirective}|${e.blockedURI}`)); });
// inject <script>inline</script> and <script src="http://127.0.0.1:OTHER/probe.js"> → expect script-src-elem violations, probe server got 0 hits
// control: page.setContent("<script>window.__c=true</script>") without CSP → __c === true
```
