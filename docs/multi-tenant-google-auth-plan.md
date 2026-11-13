# Multi-tenant Google authentication and data isolation plan

## Goal

Allow anyone to register with Google and receive a private PulseOS workspace. Preserve the existing React + TypeScript frontend, FastAPI backend, and Render deployment. Do not expose the current shared administrator workspace during migration.

## Target architecture

- **Identity:** Supabase Auth with Google OAuth. Public sign-up is enabled. The browser receives a short-lived Supabase access token.
- **API authentication:** FastAPI validates Supabase JWTs using the project's published signing keys (JWKS) and validates issuer, audience, expiry, and signature. The API derives the user ID from the verified token; it never trusts a user ID supplied in request bodies or query parameters.
- **Database:** Supabase PostgreSQL. Every tenant-owned row carries a non-null `user_id` referencing the authenticated Supabase user. Queries and mutations are scoped by that ID. Enable and test PostgreSQL Row Level Security (RLS) on tenant-owned tables. Do not expose a service-role key to the browser.
- **Files:** Supabase Storage with private buckets and user-scoped object paths/policies. File metadata is associated with an owner. Downloads use authenticated API checks or short-lived signed URLs.
- **Application:** Existing React modules and FastAPI analytics/ML services remain. The API passes the verified owner context through dataset selection, analytics, experiments, strategy, churn, anomaly, document retrieval, deletion, and exports.
- **Hosting:** Render continues to host the static frontend and FastAPI API. Supabase provides identity, durable PostgreSQL and object storage.

## Existing shared-data risks to resolve

The current implementation has one HTTP Basic administrator credential, a shared SQLite database, a global `active_datasets` selection keyed only by dataset type, and shared `raw` / `documents` directories. Simply adding Google login to the frontend would NOT isolate data. The existing routes and services must be changed together before public registration is enabled.

## Phased rollout and release gates

### Phase 0 — Preserve and inventory (this document)

- Keep current production Basic-auth behavior unchanged.
- Inventory all tables, filesystem writes, dataset selectors, service functions, and routes.
- Decide the Supabase project, Google OAuth consent configuration, redirect URLs, and secrets before enabling the new login.

### Phase 1 — Identity foundation

- Add Supabase browser client and Google sign-in/sign-out.
- Add backend JWT verification using Supabase JWKS.
- Add a development-only compatibility path for existing local tests; production must require verified bearer tokens once the cutover is ready.
- Do not make authenticated workspace routes public.

**Gate:** Test valid token, missing token, invalid signature, wrong issuer/audience, expired token, and logout.

### Phase 2 — Tenant-owned persistence

- Introduce PostgreSQL migrations and a repository/data-access layer.
- Add `user_id` to every tenant-owned entity, including datasets, active selections, experiments and any derived/persisted records.
- Scope every SELECT, INSERT, UPDATE and DELETE by verified user ID.
- Move raw uploads and extracted documents to private Supabase Storage; scope object paths and storage policies to the owner.
- Plan a deliberate migration for any existing admin data. Do not silently assign old shared data to every new user.

**Gate:** Create two test accounts. Verify each account can list, select, preview, analyse, download and delete only its own data. Attempt cross-user access by substituting IDs and object paths; every attempt must be denied.

### Phase 3 — Scope every module

Audit and secure all API families: datasets, analytics, Voice of Customer, AI Analyst/document retrieval, opportunities, experiments/decisions, strategy, health scorecard, segments, journeys, diagnostics/root cause, anomaly detection and churn prediction.

Ensure background processing and cached/model results are also tenant-scoped. Do not rely on frontend filtering for security.

**Gate:** Automated two-user isolation tests cover every route family and file operation.

### Phase 4 — Controlled production cutover

- Configure Supabase Google provider, authorized origins and exact Render callback URLs.
- Set Render environment variables for Supabase URL, anon/public key, JWT issuer/audience/JWKS configuration, and server-only database/storage credentials as required.
- Deploy backend and frontend while the old admin path remains available only as a rollback mechanism.
- Enable public Google registration only after all isolation gates pass.
- Remove HTTP Basic admin authentication only after the new flow is verified in production.

**Gate:** Production smoke tests with two independent Google accounts. Confirm one user cannot read or alter the other's data.

## Secrets and configuration policy

Never commit OAuth client secrets, Supabase service-role keys, database passwords, or signing secrets. Store them only in Render environment settings and local untracked environment files. The Supabase anon/publishable key may be used in the browser only with correctly configured RLS and storage policies. Keep service-role credentials exclusively on the backend.

## Free-tier and operational considerations

Supabase free-tier quotas, inactivity pausing, egress, storage and database limits apply. Render free web services can sleep and have ephemeral filesystems; therefore durable user data must not depend on the Render filesystem. Set upload limits, quotas, retention rules and clear demo-data guidance before inviting recruiters.

## Explicit non-goals for the first release

- No paid AI APIs.
- No separate deployment per recruiter.
- No frontend-only access control.
- No public access to the existing shared administrator data.
- No migration or deletion of existing data without an explicit backup and ownership decision.


## Implementation status — JWT identity foundation branch

The branch `feat/supabase-multitenant-foundation` adds an initial backend identity-verification layer:

- FastAPI can validate asymmetric Supabase access tokens against the project's JWKS endpoint, issuer and the `authenticated` audience.
- `GET /api/auth/me` returns the verified subject and email; it does not accept a caller-supplied user ID.
- The frontend can retrieve its existing PKCE session access token and ask the API to verify it.
- The existing HTTP Basic workspace routes remain unchanged. This is deliberate: no user is granted access to shared SQLite/files until tenant storage is implemented.

Required Render backend environment variables for this identity endpoint:

- `SUPABASE_URL=https://<project-ref>.supabase.co`
- `SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1`

No service-role key or database password is required for this identity-only step. Do not put either secret in the frontend. The current branch is an identity foundation, not a completed multi-tenant release; PostgreSQL persistence, RLS, private Storage policies, module scoping and two-user tests remain release blockers.
