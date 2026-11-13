# Security and tenant isolation

This document records the implemented Google-workspace tenant architecture and its current release boundary. It supersedes the original forward-looking migration checklist.

## Identity and API authentication

- Google OAuth is provided by Supabase Auth using an authorization-code PKCE flow.
- The browser stores the Supabase session in session storage.
- The frontend sends the access token as a Bearer token to protected workspace APIs.
- FastAPI verifies asymmetric JWT signatures using the Supabase JWKS endpoint and validates issuer, audience and required claims.
- The authenticated owner is derived from the verified token subject. Client-supplied owner IDs are not authoritative.
- `GET /api/auth/me` exposes the verified identity for the frontend's authentication check.

## Tenant-owned data

The Supabase migration `supabase/migrations/20261113000100_pulseos_tenant_foundation.sql` establishes:

- `pulseos_workspaces`, one row per authenticated user.
- `pulseos_datasets`, owner-scoped dataset metadata.
- `pulseos_active_datasets`, owner-scoped active dataset selection.
- Private Storage bucket `pulseos-private`.

RLS policies restrict tenant table operations to the authenticated user. Storage policies scope object access to objects whose first path segment is the authenticated user's ID. Dataset object paths use:

```text
<user-id>/<dataset-id>/<filename>
```

The backend repository forwards the user's access token to Supabase PostgREST and Storage. The browser receives only the Supabase publishable key; never put a service-role key, database password or signing secret in frontend code.

## Dataset API

Authenticated dataset endpoints are rooted at `/api/workspace/datasets`:

- Inspect CSV/XLSX before upload.
- Upload events and reviews.
- Extract and upload PDF/DOCX text.
- List owned datasets and active selections.
- Change the active dataset.
- Preview and delete owned datasets.

Uploaded tabular files are capped at 20 MB and document uploads at 15 MB in the implemented API. The document flow stores extracted text and metadata rather than the original binary. Scanned PDFs without embedded text are not supported because OCR is not enabled.

## Analytics request context

For enabled Google-workspace analytics routes, request-scoped context loads the authenticated user's active datasets from the private repository and makes the corresponding DataFrames/document text available to analytics services. The context is reset after the request. This avoids using the old global active-dataset selector for those enabled request paths.

The enabled scope includes Product Analytics, Voice of Customer, AI Analyst/document retrieval, Opportunities, Cohorts/Segments, Journeys/Funnels, Anomaly Detection and Churn Prediction.

## Live isolation test record

Two independent Google accounts were used to test the deployed dataset APIs and frontend:

| Operation | Result |
|---|---|
| Account A uploads an event dataset | Success |
| Account A lists and previews its own dataset | Success |
| Account B lists Account A's dataset | Not visible |
| Account B previews Account A's dataset ID | Denied (404) |
| Account B deletes Account A's dataset ID | Denied (404) |
| Account B uploads and uses its own dataset in the frontend | Success |

This is a live smoke-test record for the listed operations, not a penetration test or independent security certification.

## Explicit release boundary

The following modules remain hidden for Google-authenticated users because their persistence and tenant isolation are not part of the current enabled scope:

- Experiments
- Strategy & Insights
- Health Scorecard
- Root Cause Explorer

Do not describe every legacy module, persisted analytical artifact, background task or export path as fully tenant-isolated. The current implementation is a controlled portfolio-demo scope, not a complete production SaaS migration.

## Operational caveats

- Render free web services may sleep and use ephemeral local filesystems.
- Tenant dataset metadata and uploaded dataset objects are stored in Supabase, not dependent on Render's local disk.
- Supabase free-tier limits, availability and inactivity policies apply.
- This project has not undergone a formal security audit.
- Role-based access control, audit logs, quotas, retention automation, rate-limit policy and enterprise operational controls are not claimed as implemented.
