# PulseOS — Product Intelligence Platform

<p align="center">
  <strong>Turn product events and customer feedback into evidence-led product decisions.</strong>
</p>

<p align="center">
  <a href="https://pulseos-frontend.onrender.com">Live demo</a> ·
  <a href="https://github.com/tomerdivyanshu456-ship-it/PulseOS">Source code</a> ·
  <a href="https://github.com/tomerdivyanshu456-ship-it/PulseOS/tree/main/docs">Architecture & demo docs</a>
</p>

PulseOS is a multi-user product analytics and product intelligence portfolio application. It brings behavioural event data and customer feedback into one workspace so a product team can understand what users do, identify friction, investigate opportunities and make better-informed decisions.

**Core workflow:** measure product behaviour → understand customer feedback → identify opportunities → investigate signals → make product decisions.

> **Demo data:** Included CSV files are synthetic and intended only to demonstrate workflows. They are not real customer records, and their outputs must not be presented as actual business performance.

## Live demo

**[Open PulseOS](https://pulseos-frontend.onrender.com)**

1. Sign in with Google.
2. Upload the sample event and review CSVs from the **Upload Data** section.
3. Open Product Analytics to explore behavioural metrics.
4. Open Voice of Customer to explore review feedback.
5. Sign in with a second Google account to see a separate workspace.

The deployed Google workspace currently exposes the core modules listed below. Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer are intentionally hidden for Google-authenticated users while their persistence and tenant isolation are outside the current release scope.

## Why I built it

Product teams often inspect behavioural analytics in one tool and customer feedback in another. This makes it harder to connect what users are doing with the problems they describe.

PulseOS explores a practical workflow for combining these signals without pretending that correlation proves causation. It is designed as a product decision-support tool, not an autonomous product manager or a replacement for a production analytics stack.

## Product capabilities

| Area | What it helps answer |
|---|---|
| **Overview & Product Analytics** | How are active users, conversion, revenue, funnels and retention changing in the uploaded event data? |
| **Voice of Customer** | What themes appear in customer reviews, and how are ratings and sentiment distributed? |
| **AI Analyst** | Which source passages support a question about uploaded data or PDF/DOCX documents? |
| **Product Opportunities** | Which feedback themes may deserve further behavioural investigation? |
| **Cohorts & Segments** | How do engagement and purchasing metrics differ across user attributes and cohorts? |
| **Funnel & Journeys** | Where do users drop off in an ordered journey, and which paths do they take? |
| **Anomaly Detection** | Which daily product activity metrics look unusual relative to recent history? |
| **Churn Prediction** | Which behavioural patterns distinguish users who become inactive in a defined follow-up window? |
| **Upload Data** | How can a user upload, inspect, activate and manage their own event, review and document sources? |

### Current Google-workspace availability

The deployed Google-authenticated experience enables the core data workflow: Overview, Upload Data, Product Analytics, Opportunities, Voice of Customer, AI Analyst, Cohorts & Segments, Funnel & Journeys, Anomaly Detection and Churn Prediction.

The following modules are not currently exposed in the Google workspace: **Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer.** They are not represented as completed multi-tenant features.

## Architecture

PulseOS uses a React frontend, a FastAPI backend and Supabase for user identity and tenant-owned dataset persistence.

```text
                   Google sign-in
                        │
                        ▼
                 Supabase Auth
              (OAuth + PKCE session)
                        │
                 Supabase access JWT
                        │
                        ▼
React + TypeScript ──► FastAPI API
                        │
                 Verify JWT signature,
                 issuer, audience, claims
                        │
                 derive owner from sub
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
      Supabase Postgres      Supabase Storage
      + Row Level Security   private bucket
      workspace/dataset      owner-scoped object
      metadata + active      paths and policies
      dataset selection
             │                     │
             └──────────┬──────────┘
                        ▼
              Workspace data context
                        │
                        ▼
             Pandas / analytics / ML
                        │
                        ▼
              Workspace-scoped API
                        │
                        ▼
                 React dashboards
```

### Main technology choices

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | Python, FastAPI, Pandas |
| Authentication | Supabase Auth, Google OAuth, PKCE |
| API identity verification | Supabase JWT/JWKS verification |
| Tenant-owned persistence | Supabase PostgreSQL with Row Level Security |
| Uploaded dataset storage | Private Supabase Storage bucket |
| Analytics & machine learning | NumPy, Pandas, scikit-learn |
| Visualisation | Recharts |
| Testing | Pytest, FastAPI TestClient, TypeScript/Vite build |
| Hosting | Render (frontend and API), Supabase (auth and data) |

## Multi-user security model

Tenant isolation is enforced by the backend and Supabase policies, not by hiding rows in the frontend.

- Users authenticate through Google OAuth via Supabase Auth.
- FastAPI verifies Supabase access tokens using the project's published JWKS and validates token claims.
- The backend derives the authenticated user ID from the verified token subject; it does not trust a caller-supplied owner ID.
- Workspace and dataset metadata are stored in Supabase PostgreSQL with Row Level Security.
- Uploaded files are stored in a private Supabase Storage bucket under owner-scoped paths.
- Dataset list, active selection, preview, retrieval and deletion operations use the authenticated user's access token and ownership policies.
- The backend does not expose a Supabase service-role key to the browser.

### Isolation verification

The live two-account test covered the following scenario:

| Test | Expected result | Observed result |
|---|---|---|
| Account A uploads a dataset | Upload succeeds for A | Passed |
| Account A lists and previews its dataset | A can access its own data | Passed |
| Account B lists datasets | A's dataset is not listed | Passed |
| Account B previews A's dataset by ID | Access is denied | Passed (404) |
| Account B deletes A's dataset by ID | Access is denied | Passed (404) |
| Account B uploads its own dataset | B sees its own workspace data | Passed in live frontend test |

These are application-level verification results for the tested dataset operations, not a claim of a formal third-party security audit. The current tenant-scoped release is intentionally limited to the modules identified above; unfinished modules remain unavailable to Google workspaces.

More detail: [Security and tenant isolation](docs/multi-tenant-google-auth-plan.md).

## Data ingestion

PulseOS supports user-uploaded datasets and document sources.

### Behavioural event CSV

| Column | Required | Description |
|---|---|---|
| `user_id` | Yes | Stable user identifier |
| `event_name` | Yes | Event or action name |
| `timestamp` | Yes | Parseable event timestamp |
| `session_id` | No | Session identifier for session-level journeys |
| `revenue` | No | Revenue value on purchase events |
| Other categorical columns | No | Useful for segment comparisons |

### Customer review CSV

| Column | Required | Description |
|---|---|---|
| `review_id` | Yes | Review identifier |
| `rating` | Yes | Numeric rating from 1 to 5 |
| `review_text` | Yes | Review text |

Optional fields such as `review_date` and `product_category` provide additional context.

### Documents

PDF and DOCX files can be uploaded for text extraction and retrieval in AI Analyst. The current pipeline extracts embedded text; scanned PDFs without a text layer are not searchable because OCR is not enabled. Extracted text is stored in the private workspace storage. The current document upload flow stores extracted text and filename metadata rather than preserving the original binary file.

### Included synthetic datasets

- `data/sample_user_events.csv` — behavioural events for core product analytics.
- `data/sample_customer_reviews.csv` — ratings and review text for Voice of Customer.
- `data/sample_churn_events.csv` — synthetic history for demonstrating the inactivity prediction workflow.

The churn sample uses a constructed inactivity outcome. Do not interpret its labels or model metrics as real customer behaviour.

## Analytics and ML methodology

PulseOS favours interpretable methods and discloses important limitations.

- **Product metrics:** calculated from the uploaded event window. DAU is distinct active users on the latest recorded calendar day; MAU uses the available 30-day window.
- **Funnels:** configurable ordered event steps. Session-level units are used when `session_id` is available; otherwise the analysis falls back to user-level units.
- **Cohorts and segments:** comparisons are descriptive and depend on the available event observation window.
- **Voice of Customer:** lightweight text, sentiment and complaint-theme methods support triage; they are not a substitute for qualitative research or a validated language model.
- **Opportunity signals:** review themes and behavioural patterns are compared at theme level. Unrelated third-party reviews are not joined to individual behavioural user IDs.
- **AI Analyst:** document retrieval is extractive and evidence-oriented. It returns relevant source passages rather than generating unsupported answers.
- **Document retrieval:** optional MiniLM semantic embeddings can be used locally; TF-IDF unigram/bigram cosine retrieval is the fallback. Retrieval scores indicate relevance, not truth or confidence.
- **Anomaly detection:** Isolation Forest flags unusual daily metrics. Flags are investigation leads, not proof of incidents.
- **Churn prediction:** churn is operationalised as inactivity in a defined follow-up window. This is an inactivity proxy, not confirmed cancellation; holdout scores are retrospective, not live customer risk predictions.

### AI Analyst: retrieval, not generative AI

The AI Analyst is not powered by a hosted generative LLM. It retrieves relevant evidence from the selected document source and returns extractive passages with filename and chunk-level references. Optional semantic retrieval uses `sentence-transformers/all-MiniLM-L6-v2`; TF-IDF retrieval is available as a lighter fallback. No paid API key is required.

Semantic model weights may need to be downloaded on first use. The model runs on CPU and is cached in-process. Scanned-document OCR and PDF page-offset citations are not currently supported.

## Local development

### Prerequisites

- Python 3.11+
- Node.js LTS
- Git
- A Supabase project configured with Google OAuth for the authenticated workspace flow

### 1. Clone the repository

```powershell
git clone https://github.com/tomerdivyanshu456-ship-it/PulseOS.git
cd PulseOS
```

### 2. Configure the backend

Copy the example file and fill in your own Supabase project values. Do not commit local environment files or secrets.

```powershell
cd backend
Copy-Item .env.example .env
```

Set these backend variables in your local environment or `.env` according to your environment loader:

- `SUPABASE_URL` — Supabase project URL.
- `SUPABASE_JWT_ISSUER` — `https://<project-ref>.supabase.co/auth/v1`.
- `SUPABASE_PUBLISHABLE_KEY` — Supabase publishable key used for user-token requests subject to RLS.
- `PULSEOS_CORS_ORIGINS` — include `http://localhost:5173` for local frontend development.
- `PULSEOS_ENV=development`.

Create and activate a virtual environment, install dependencies and start the API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

### 3. Configure and start the frontend

Open a second PowerShell terminal:

```powershell
cd frontend
Copy-Item .env.example .env
```

Set the frontend values in `frontend/.env`:

- `VITE_API_BASE_URL=http://127.0.0.1:8000`
- `VITE_SUPABASE_URL` — same Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY` — the project's publishable key.

Then run:

```powershell
npm install
npm run dev
```

Open http://localhost:5173. Configure the Supabase Google provider and add the local origin/redirect URL to the Supabase Auth URL configuration. The backend CORS allowlist must include the local frontend origin.

> Do not use production secrets in a local environment, commit `.env` files, or expose server-only credentials in frontend variables. The publishable key is intended for client use with correctly configured RLS; service-role keys and database passwords must remain server-side.

## Deployment

The hosted demo uses Render for the frontend and FastAPI service, and Supabase for Google authentication, PostgreSQL metadata and private object storage.

- Frontend: https://pulseos-frontend.onrender.com
- Backend health endpoint: https://pulseos-api-99m1.onrender.com/api/health
- API OpenAPI schema: https://pulseos-api-99m1.onrender.com/openapi.json

**Free-tier caveats:** Render free web services may sleep and have ephemeral local filesystems. User-owned dataset metadata and uploaded data for the tenant workflow are stored in Supabase rather than relying on the Render filesystem. Supabase free-tier quotas, availability and inactivity policies still apply. The hosted instance is a portfolio demo, not a production SLA-backed service.

## Quality checks

Run backend tests from `backend/`:

```powershell
python -m pytest -q
```

Build the frontend from `frontend/`:

```powershell
npm.cmd run build
```

The project has a backend test suite covering authentication, workspace/dataset APIs and service behaviour. Run the commands above on the current checkout before making a release; test counts can change as the code evolves.

## Known limitations and next engineering steps

- Four modules remain hidden from Google workspaces: Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer.
- The current tenant migration covers the Google-workspace data path and enabled modules, not every legacy module or every persisted analytical artifact.
- The app is a portfolio MVP, not a production SaaS offering with a formal security audit, billing, role-based access control, audit trails, service-level objectives or enterprise operations.
- Scanned PDF OCR and original document-binary retention are not implemented in the current document flow.
- Some analytics and ML outputs are descriptive, heuristic or retrospective. They must not be described as causal proof or production predictions.
- Free hosting tiers can have cold starts, quota constraints and service interruptions.

## Project positioning

PulseOS demonstrates product thinking, full-stack implementation, practical analytics, applied machine learning, evidence-aware AI retrieval and multi-user data isolation. It is intended as a portfolio project for Product Analyst, Data Analyst, Business Analyst and AI Product roles.

It is not marketed as a production-ready enterprise analytics platform.
