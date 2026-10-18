# Akam backend: handoff and go-live to-do

Read this first. It tells you what the backend is for, what is already done, what the Flutter app expects, and what is left to make it live. A ready-to-paste prompt for your IDE agent is at the end.

Last updated 2026-10-18. Backend repo state: clean working tree, latest commit `cfa2cff` (OTP auth, sessions, config endpoints, health probes). 73 pytest tests passed when last run.

---

## 1. Why the backend looks like this

The Flutter app (`C:\Users\LENOVO\Desktop\Akam`) is now **local-first**:

- Personal content (chat messages, memories, events, files, notes, people) lives in an **encrypted database on the phone** (Drift + SQLCipher). It must never reach this server in readable form.
- **Ilango, the AI, runs on the phone** (Gemma 4 E2B through LiteRT-LM). The server does no LLM work for the new app.
- This server therefore only does: **account and login, token refresh, device records, the on-device model manifest, app config, health, and (still to build) anonymous analytics and encrypted backup blobs.**

Consequence: the old content endpoints (`/chat`, `/graph`, `/clusters`, `/events`, `/nudges`, `/briefing`, `/search`, `/digest`, `/dashboard`, `/notifications`, `/files`, `/feed`, `/memories`) are **deprecated**. They still work so old builds do not break, and are marked `deprecated=True` in `app/main.py`. They get deleted once no app build calls them.

Stack: FastAPI, async SQLAlchemy 2, Postgres (Supabase) through asyncpg, Alembic migrations, RS256 JWTs, deployed on Vercel (`vercel.json` routes everything to `api/index.py`).

---

## 2. What is already done (Phase 0)

| Area | State |
|---|---|
| Config | `app/config.py`: `development / staging / production` settings, fail-fast on missing secrets outside development, no insecure default secret, CORS allow-list (no `*`), RS256 keys from env as PEM text. `.env.example` lists every variable. |
| Database | Postgres via `DATABASE_URL` (asyncpg). `app/db/session.py` uses NullPool and `statement_cache_size=0` so it is safe on Vercel and behind Supabase's pgbouncer. Alembic is set up (`alembic.ini`, `migrations/`), with `0001_initial` and `0002_auth_otp_sessions`. SQLite is for pytest only. |
| Auth | Passwordless **email OTP**: `POST /api/v1/auth/request-otp`, `POST /api/v1/auth/verify-otp`. Codes are 6 digits, hashed at rest, expire in 10 min, max 5 attempts, rate-limited per email and per IP. Refresh tokens and revocations are stored in the database. `/auth/refresh` rotates tokens and detects reuse. `expires_in` now reports the real TTLs (access 1 h, refresh 30 d). |
| Old login | `POST /auth/register` still exists behind `ENABLE_LEGACY_REGISTER=false`. It was an account-takeover hole (trusted `device_id` alone). Keep it off. |
| Config endpoints | `GET /api/v1/config/models` (public) and `GET /api/v1/config/app`. |
| Health | `GET /api/v1/health` and `GET /api/v1/ready`. |
| Hardening | Per-endpoint rate limits, idempotency scoped by user, structured logging, unhandled exceptions logged. |
| Docs | `akam_api_contract.md` updated for the above. |

Key files: `app/main.py`, `app/config.py`, `app/db/session.py`, `app/routers/auth.py`, `app/routers/config.py`, `app/routers/health.py`, `app/security/jwt.py`, `app/security/identity.py`, `app/services/email_service.py`, `app/models/db/auth.py`, `migrations/versions/`, `tests/test_phase0.py`.

**Not verified:** the real Supabase and Vercel deployment, real SMTP delivery, and behaviour of the in-memory rate limiter across several serverless instances. Alembic was only run against a local Postgres.

---

## 3. API contract the Flutter app depends on

All responses use the envelope `{"success": bool, "data": {...}, "error": ..., "timestamp": "..."}`. The app reads `body["data"] ?? body`. **Do not change the envelope.**

Base URL in the app: `https://akam-backend.vercel.app/api/v1` (constant in the app's `lib/services/api_client.dart`; change it there if the domain changes).

| Endpoint | Request | Response `data` |
|---|---|---|
| `POST /auth/request-otp` | `{email, device_id}` | `{sent, expires_in}` |
| `POST /auth/verify-otp` | `{email, code, device_id, language, fcm_token?, device_platform}` | `{user_id, access_token, refresh_token, device_secret, is_new_user, token_type, expires_in, refresh_expires_in}` |
| `POST /auth/refresh` | `{refresh_token, device_secret}` | `{access_token, refresh_token, token_type, expires_in, refresh_expires_in}` |
| `POST /auth/logout` | `{refresh_token}` | `{revoked}` |
| `POST /auth/logout_all` | (auth header) | `{sessions_revoked}` |
| `PUT /auth/device` | `{fcm_token, device_platform}` | `{updated}` |
| `GET /config/models` | none, public | `{version, url, sha256, size_bytes}` |
| `GET /config/app` | none | `{min_app_version, feature_flags}` |

### Cross-repo gotchas (the app side is not updated yet)

1. **`device_secret` is shown once at verify and required by `/auth/refresh`.** The Flutter client currently refreshes with only `refresh_token` (`ApiClient._refreshToken`), so refresh will return 422 until the app stores the secret and sends it. That is app work, not backend work, but do not "fix" it by loosening the server.
2. The app still calls the old `/auth/register`. It is off, so **the current app build cannot sign in to this backend** until the app's email-code screens are done.
3. `GET /config/models` returns 404 `MODEL_MANIFEST_NOT_CONFIGURED` if the model env vars are empty. The app falls back to a built-in manifest in that case, so this is not fatal, but set them.

---

## 4. Go-live to-do (in order)

### A. Accounts and secrets (human steps)
- [ ] Create a **Supabase** project. Note the region.
- [ ] Get two connection strings: the **pooled** one (port 6543, transaction mode) for runtime, and the **direct or session** one (port 5432) for migrations. Format: `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/postgres?ssl=require`.
- [ ] Generate the RS256 keypair (commands are in `.env.example`). Store both as PEM text in Vercel env vars, with `\n` for newlines if single-line.
- [ ] Generate `OTP_HASH_SECRET` (`openssl rand -hex 32`).
- [ ] Choose SMTP (decided). Get host, port (587), user, password, and a verified sender address. Set `EMAIL_BACKEND=smtp`.
- [ ] Decide the final API domain and set `ALLOWED_ORIGINS` (exact origins only).

### B. Environment variables to set in Vercel (Production)
| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | pooled Supabase URL (6543) |
| `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` | PEM text |
| `OTP_HASH_SECRET` | random hex |
| `EMAIL_BACKEND` | `smtp` |
| `EMAIL_FROM` | `Akam <no-reply@yourdomain>` (sender must be verified with the SMTP provider) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | from provider |
| `ENABLE_LEGACY_REGISTER` | `false` |
| `ALLOWED_ORIGINS` | explicit list |
| `MODEL_VERSION` | `gemma-4-e2b-it` |
| `MODEL_URL` | `https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it.litertlm` |
| `MODEL_SHA256` | `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c` |
| `MODEL_SIZE_BYTES` | `2588147712` |
| `MIN_APP_VERSION` | `1.0.0` |
| `FEATURE_FLAGS` | `{}` |

Never commit real values. The model file is public and Apache-2.0 on Hugging Face (no token needed). Mirror it to your own storage before real launch so you do not depend on Hugging Face availability; if you do, change only `MODEL_URL` (checksum stays the same if the file is identical).

### C. Deploy and migrate
- [ ] Run migrations against Supabase with the **direct/session** URL: `DATABASE_URL=<direct url> alembic upgrade head`. Do this from a trusted machine, not from Vercel.
- [ ] Deploy to Vercel (`vercel --prod`, or connect the repo). Confirm the function builds (check Python version and dependencies in `pyproject.toml` / `requirements.txt`).
- [ ] Smoke test (see section 6).

### D. Backend code still to build
1. [x] **Anonymous analytics ingest.** `POST /api/v1/analytics/events`, auth required.
   - Body: `{"anon_id": "<rotating uuid>", "app_version": "1.0.0", "events": [{"name": "screen_view", "ts": "2026-10-18T10:00:00Z", "props": {"screen": "home"}}]}` (max 100 events per request).
   - **Allow-list validation is the privacy guarantee.** Accept only known event names and known prop keys with short enum/number values. Reject (422) anything containing free text such as message text, file names, or person names. Tested that a prop named `text` or a string over 40 chars is rejected.
   - Stored in `analytics_events` table with no user email or user id (`anon_id` only). Migration `0003` applied.
2. [x] **Encrypted backup blobs.** `PUT /api/v1/backup`, `GET /api/v1/backup`, `GET /api/v1/backup/download`, `DELETE /api/v1/backup`, auth required.
   - The blob is **opaque ciphertext** produced on the phone. The server never has the key and must never try to parse it.
   - `PUT`: multipart upload plus headers `X-Backup-Version`, `X-Backup-Sha256`. Enforces 50MB limit. Keeps the last 5 versions per user.
   - `GET`: returns the latest blob metadata. `GET /download`: streams raw encrypted bytes. `DELETE`: removes all of the user's backups.
3. [x] **Real account deletion.** `DELETE /user/data` completely deletes the user, devices, sessions/refresh tokens, and backups in one transaction. Tested that zero rows remain for the user.
4. [ ] **Retire content endpoints.** (Held pending confirmation from Flutter app team).
5. [x] **Serverless limiter fix.** OTP request limits are enforced durably in Postgres (`OtpCode` query within window).
6. [x] **CI.** Added GitHub Actions `.github/workflows/ci.yml` with PostgreSQL 16 container, alembic migrations, and pytest test suite. `uv.lock` is tracked.
7. [x] **Contract and docs.** `akam_api_contract.md` updated with Section 16 for analytics and backups.

### E. Hand-back to the app
- Tell the app team when the API is live and the final base URL.
- The app then switches login to email-code, stores `device_secret`, and sends it on refresh.

---

## 5. Known issues found in the exploration (fix or consciously accept)

- `datetime.utcnow()` is used in many places (deprecation warnings in pytest). Switch to timezone-aware UTC.
- `get_subgraph` in the graph router did not filter by `user_id` (an IDOR). It disappears when graph is retired; if retirement slips, fix it.
- Several mock routers return hardcoded data. They are deprecated; do not invest in them.
- WebSocket `/ws` has no server push. Remove it unless a use appears.
- Pagination cursors are returned but never accepted in the old routers. Irrelevant if they are retired.
- Contract drift: the old envelope fields `status` and `meta` are converted by a validator, so bodies carry `success/data/error/timestamp`. The contract file was updated, re-check it.

---

## 6. Smoke test after deploy

```bash
BASE=https://<your-domain>/api/v1
curl -s $BASE/health
curl -s $BASE/ready
curl -s $BASE/config/models
curl -s -X POST $BASE/auth/request-otp -H 'content-type: application/json' \
  -d '{"email":"you@example.com","device_id":"test-device-0123456789"}'
# read the code from your inbox, then:
curl -s -X POST $BASE/auth/verify-otp -H 'content-type: application/json' \
  -d '{"email":"you@example.com","code":"123456","device_id":"test-device-0123456789"}'
# use the returned refresh_token and device_secret:
curl -s -X POST $BASE/auth/refresh -H 'content-type: application/json' \
  -d '{"refresh_token":"...","device_secret":"..."}'
```

Check: health is 200, `ready` reports the database reachable, an OTP email arrives, a wrong code is rejected, the sixth attempt is blocked, refresh with a used refresh token is rejected (reuse detection), logout then refresh fails.

Local commands: `uv sync`, `uvicorn app.main:app --reload --port 8000`, `pytest tests -q`, `alembic upgrade head`, `alembic revision --autogenerate -m "msg"`.

---

## 7. Prompt to paste into the IDE agent

> You are working in the Akam FastAPI backend. Read `BACKEND_HANDOFF.md` fully, then `akam_api_contract.md`, `app/config.py`, `app/routers/auth.py`, and `app/db/session.py`. The backend serves a local-first mobile app: no personal content may be stored on this server in readable form. Do not change the response envelope `{success, data, error, timestamp}` and do not re-enable `ENABLE_LEGACY_REGISTER`.
> Do section 4D in this order, each with pytest tests and an Alembic migration where the schema changes: (1) analytics ingest with strict allow-list validation, (2) encrypted backup endpoints (opaque blobs, size limit, versions, Supabase Storage signed URLs preferred), (3) real account deletion, (5) move OTP rate limits to Redis/Upstash or Postgres, (6) CI. Do not do item 4 (retire content endpoints) until I confirm. Never print, log, or commit secrets. Run `pytest tests -q` and `alembic upgrade head` against a throwaway Postgres before reporting. Finish with a list of anything you could not verify.
