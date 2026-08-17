# Phase 11 Development Report — Production Hardening

## Completed

This phase worked through the accumulated gaps flagged across Phases 1–10's "Known Issues"
sections, plus the standard production-readiness checklist for a FastAPI service.

- **Refresh tokens** (flagged since Phase 1): `RefreshToken` model stores only a SHA-256
  hash of each token, never the raw value — a database compromise alone can't be used to
  mint sessions. `/auth/login` now returns both an access token and a refresh token;
  `/auth/refresh` exchanges a valid refresh token for a new pair and **revokes the one
  presented in the same operation** (rotation) — replaying an old refresh token after it's
  been exchanged is rejected, limiting a leaked token's usefulness to a single exchange.
  Verified live over real HTTP: exchanged a token successfully, then confirmed reusing the
  same token was rejected with 401.
- **`create_all()` gated to non-production** (flagged since Phase 1): in production mode,
  the app skips the dev-bootstrap `Base.metadata.create_all()` entirely and relies solely on
  Alembic migrations, so a missing/failed migration in a shared environment can't be
  silently masked by the convenience call.
- **Environment-driven CORS**: replaced the hard-coded `localhost:5173` origin with a
  `CORS_ORIGINS` environment variable (comma-separated list), defaulting to the dev origin
  only — a production deployment must explicitly set its real origins.
- **Startup safety check**: the app refuses to start in production mode if `SECRET_KEY` is
  still the insecure default, raising a clear `RuntimeError` rather than silently running
  with a guessable JWT signing key.
- **Global exception handlers**: every error response — a normal 4xx, a validation failure,
  or a genuinely unhandled exception — comes back as consistent `{"detail": ...}` JSON.
  An unhandled exception is logged with a full traceback server-side but returns a generic
  message to the client, never a stack trace.
- **Structured logging + request tracing**: every request gets an `X-Request-ID` (generated
  or passed through from the caller), logged alongside the method/path/status, so a single
  request can be traced through logs even under concurrent load. Verified live: the header
  is present on every response.
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin` on every response. Deliberately does
  **not** set a Content-Security-Policy — see Known Issues for why.
- **Rate limiting**: a basic fixed-window limiter (100 requests/60s per client IP),
  **scoped to production only**. See "A bug caught mid-phase" below for why.
- **CI workflow** (`.github/workflows/ci.yml`): runs the full backend test suite (via a
  fresh SQLite database with Alembic migrations applied) and the frontend production build
  on every push/PR to `main`.
- **Frontend refresh-token integration**: the auth store now persists both tokens; `api.js`
  silently retries a request exactly once after refreshing the access token on a 401, only
  falling back to logout + redirect if the refresh itself fails — so a merely-expired access
  token no longer interrupts the user's work.

## A bug caught mid-phase (not hidden)

The first version of `RateLimitMiddleware` was added unconditionally to `app`. Running the
full test suite immediately after produced 5 unrelated-looking failures
(`test_inventory_api.py`, `test_purchases_api.py`, `test_reports_api.py`,
`test_sales_api.py`, `test_tax_api.py` — all `KeyError` on a response body that turned out
to be a 429 rate-limit rejection, not the expected 200/201). The root cause: the FastAPI
`app` object is a module-level singleton created once at import time, so
`RateLimitMiddleware`'s in-memory hit-counter **persisted for the entire pytest process**,
accumulating requests across every test file rather than resetting per test. By the time
later test files ran, earlier tests had already exhausted the 100-request budget.

Fixed by scoping rate limiting to production only (`if settings.is_production:` before
`app.add_middleware(RateLimitMiddleware, ...)`), with the reasoning documented directly in
`app/main.py`'s comment so a future reader doesn't wonder why it's conditional. Re-ran the
full suite: back to 100% passing. The middleware itself is still fully implemented and
tested — see `tests/test_rate_limit.py`, which builds an isolated single-purpose FastAPI
app rather than reusing the shared test client, specifically to avoid the same
cross-test-contamination problem in its own test.

## Files Created

**Backend**:
`app/models/refresh_token.py`, `app/core/rate_limit.py`, `app/core/security_headers.py`,
`app/core/logging_config.py`, `migrations/versions/232148160c3d_phase11_production_hardening.py`,
`tests/test_refresh_tokens.py`, `tests/test_rate_limit.py`, `tests/test_error_handling.py`.

**Root**: `.github/workflows/ci.yml`.

## Files Modified

- `app/config.py` — added `refresh_token_expire_days`, `cors_origins` (+ `cors_origin_list`
  property), `is_production` property, and a production-mode secret-key safety check.
- `app/auth/security.py` — added `generate_refresh_token()` and `hash_refresh_token()`.
- `app/api/v1/auth.py` — login now issues a refresh token; added `/auth/refresh` with
  single-use rotation.
- `app/schemas/user.py` — `Token` schema gained an optional `refresh_token` field.
- `app/main.py` — rewritten: env-driven CORS, gated `create_all`, global exception
  handlers, request-ID/logging middleware, security headers, conditional rate limiting.
- `migrations/env.py`, `tests/conftest.py` — import the new `refresh_token` model.
- `backend/.env.example` — documented the new settings.
- `frontend/src/stores/auth.js` — persists and uses the refresh token.
- `frontend/src/services/api.js` — silently retries once via refresh on a 401.

## Database Changes

Migration `232148160c3d_phase11_production_hardening` adds `refresh_tokens` (with an index
on `token_hash` for fast lookup during `/auth/refresh`). One new table, no `ALTER` on an
existing table, consistent with Phases 9–10. Verified with a full
`rm -f dev.db && alembic upgrade head` from empty, running all eleven migrations
(Phases 1–11) in sequence without error.

## Tax/Accounting Rules Added

None — this phase is infrastructure/security hardening only, with zero changes to any
posting, tax, or accounting logic anywhere in the system.

## Tests

`pytest -v` in `backend/`: **71 passed, 0 failed** (61 carried over from Phases 1–10, 10
new).

- `test_refresh_tokens.py`: login issues a refresh token alongside the access token;
  exchanging a refresh token returns a genuinely different new pair, and the new access
  token actually authenticates a real API call; a refresh token is single-use — reusing one
  after it's been exchanged is rejected with 401; an outright invalid refresh token is
  rejected.
- `test_rate_limit.py` (isolated test app, not the shared client): requests under the limit
  all succeed; requests over the limit are rejected with 429 and a clear message.
- `test_error_handling.py`: a 404 on an unknown route returns consistent `{"detail": ...}`
  JSON; a validation failure returns 422 with `detail`; every response carries an
  `X-Request-ID` header; every response carries the security headers.

The running server was smoke-tested live (uvicorn + curl): confirmed security headers and
`X-Request-ID` present on `/health`; registered a user and confirmed login returns both
tokens; exchanged the refresh token and confirmed a new pair came back; **reused the
already-exchanged token and confirmed it was correctly rejected** — the single-use rotation
behavior working exactly as the unit tests predicted, over a real HTTP round trip. The
frontend was rebuilt with `npx vite build` after the auth store/api.js changes — 106
modules, no errors.

**Passed:** 71/71 automated tests, live smoke test, frontend build. **Failed:** the rate-
limiter cross-test-contamination issue above, caught and fixed with the reasoning documented
in code — not a silent workaround.

## Known Issues

- **Rate limiting is single-process, in-memory** — it does not coordinate across multiple
  worker processes or horizontally-scaled instances. A production deployment running more
  than one process/replica needs a shared store (Redis, etc.) for the limit to be
  meaningful platform-wide rather than per-process. Documented directly in
  `app/core/rate_limit.py`'s docstring.
- **No Content-Security-Policy header** — a CSP tight enough to be meaningful has to be
  tailored to the actual frontend's script/style sources; shipping a generic one risks
  breaking the app while giving a false sense of security. Recommended to set this at the
  reverse-proxy/CDN layer instead, where it can be tuned per environment without a backend
  redeploy.
- **No account lockout after repeated failed logins** — rate limiting slows brute-force
  attempts but doesn't lock a specific account; a dedicated failed-login-attempt counter per
  user would be a reasonable addition.
- **Multi-currency remains deferred** (from Phase 10) — not revisited this phase, since it's
  a scope decision about the accounting/posting layer, not a hardening concern.
- **No automated dependency vulnerability scanning** in the CI workflow (e.g.
  `pip-audit`/`npm audit` as a CI step) — the workflow runs tests and the build, but doesn't
  yet fail on known-vulnerable dependencies.
- **No database backup/restore documentation or tooling** — production deployment
  operational concerns (backup cadence, point-in-time recovery, migration rollback testing)
  aren't covered by this delivery; they depend on the actual hosting environment chosen.
- The accumulated "no reversal/void workflow" gap from Phases 4–9 (sales invoices, purchase
  bills, cash receipts/disbursements, depreciation entries) was **not** addressed this
  phase — it's a functional/product gap, not a production-hardening one, and revisiting it
  now would risk destabilizing modules that are currently fully tested and working.

## Summary — all 11 phases

This completes the originally-scoped 11-phase roadmap: Foundation → Accounting Engine → Tax
Engine → Sales → Purchases → Banking → Philippine Compliance/BIR → Inventory → Fixed
Assets → Advanced Features (financial statements + budgeting) → Production Hardening.
**71 automated tests pass** across the full stack, every phase was verified live against a
running server in addition to the automated suite, and every SQLite/Alembic migration issue
encountered along the way was caught, fixed, and documented rather than worked around
silently. Known gaps — multi-currency, cash flow statements, document void/reversal
workflows, and the operational concerns listed above — are documented honestly per-phase
rather than glossed over, so a future team picking this up knows exactly what's solid and
what still needs work.
