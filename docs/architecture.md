# PulseOS architecture

## System context

PulseOS is a multi-user product intelligence portfolio application. The React client authenticates users with Google through Supabase Auth. The FastAPI backend verifies the resulting access token and uses the verified subject as the tenant identity. Supabase PostgreSQL and private Storage hold tenant-owned workspace and dataset records.

## Request and data flow

1. The browser initiates Google OAuth using the Supabase authorization endpoint and PKCE.
2. Supabase returns an authorization code. The frontend exchanges it for a session and keeps the session in session storage.
3. The frontend sends the access token as a Bearer token to the API.
4. FastAPI verifies the token signature against Supabase JWKS and validates issuer, audience and required claims.
5. The backend derives the owner from the verified token subject; it does not accept an arbitrary owner ID from the client.
6. The workspace API reads the caller's workspace through Supabase PostgREST under the caller's RLS context.
7. Dataset operations use the caller's JWT for Supabase PostgREST and Storage requests.
8. For enabled analytics routes, request-scoped workspace context loads that user's active events, reviews and extracted document text. Analytics services read from that context rather than the legacy global dataset selector.
9. The request context is reset after the request completes.

## Supabase tenant schema

The tenant foundation migration creates:

- `pulseos_workspaces`: one workspace row per authenticated user.
- `pulseos_datasets`: dataset metadata including owner, type, filename, object path, row count, content type and upload time.
- `pulseos_active_datasets`: active dataset selection keyed by owner and dataset type.
- `pulseos-private`: private Storage bucket for tenant-owned uploaded data.

RLS is enabled on the tenant tables. Owner policies restrict row operations to the authenticated user. Storage policies restrict objects by the first folder segment, which is the authenticated user's ID. The backend forwards the user's JWT rather than using a service-role key for these user-scoped operations.

Dataset object paths follow this shape:

```text
<authenticated-user-id>/<dataset-uuid>/<filename>
```

## API surface

The authenticated workspace data API is rooted at `/api/workspace`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/workspace` | Retrieve the authenticated user's workspace |
| POST | `/api/workspace/datasets/inspect` | Inspect CSV/XLSX data before upload |
| POST | `/api/workspace/datasets/upload/{dataset_type}` | Upload event or review data |
| POST | `/api/workspace/datasets/upload-document` | Extract and upload PDF/DOCX text |
| GET | `/api/workspace/datasets` | List caller-owned datasets |
| GET | `/api/workspace/datasets/active` | Read caller's active dataset selections |
| PUT | `/api/workspace/datasets/active/{dataset_type}` | Change active dataset |
| GET | `/api/workspace/datasets/{dataset_id}/preview` | Preview an owned dataset |
| DELETE | `/api/workspace/datasets/{dataset_id}` | Delete an owned dataset |

The API also provides JWT verification at `/api/auth/me`. Refer to the live OpenAPI schema for the exact current route definitions.

## Enabled Google-workspace analytics

The request-scoped owner context is used by the enabled Google-workspace route families, including Product Analytics, Voice of Customer, AI Analyst/document retrieval, Opportunities, Cohorts/Segments, Journeys/Funnels, Anomaly Detection and Churn Prediction.

Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer remain hidden from Google-authenticated users. Their legacy persistence and data paths are not represented as tenant-migrated.

## Security boundaries and caveats

- The frontend is not the security boundary. The API verifies identity and derives ownership from the token.
- Supabase RLS and Storage policies enforce owner boundaries for the tenant tables and uploaded objects.
- The service-role key is not sent to the browser and is not used for the user-scoped repository operations described here.
- The live two-account smoke test verified dataset upload, list, preview and delete isolation for the tested paths.
- The current implementation is not a formal security audit. It does not claim every legacy route or derived artifact has been migrated.
- Keep Supabase signing secrets, service-role credentials and database passwords out of source control and frontend configuration.

## Hosting model

Render hosts the static frontend and FastAPI API. Supabase provides Auth, Postgres and private Storage. Render free instances may sleep and have ephemeral local disks; tenant dataset persistence therefore relies on Supabase. Free-tier quotas and availability constraints apply.
