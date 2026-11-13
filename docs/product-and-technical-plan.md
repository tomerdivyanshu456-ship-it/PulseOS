# PulseOS product brief and technical direction

## Product

PulseOS is a multi-user product intelligence portfolio application that helps product teams explore behavioural event data alongside customer feedback. Its workflow is to measure product behaviour, understand customer friction, identify opportunities and support evidence-led product decisions.

## Intended users

- **Product Analysts:** explore activation, conversion, retention, funnels, cohorts and feature usage.
- **Product Managers:** identify customer problems and prioritise follow-up investigations.
- **Data Analysts / Business Analysts:** inspect uploaded datasets, build descriptive analyses and communicate findings.
- **AI Product practitioners:** evaluate evidence retrieval and applied ML workflows without overstating model capability.

## Product principles

1. Make the source and observation window of metrics clear.
2. Separate descriptive facts from heuristics and model outputs.
3. Do not present correlations as proven causes.
4. Do not join unrelated review data to individual behavioural user IDs.
5. Prefer lightweight, interpretable methods and zero-cost APIs.
6. Keep tenant-owned data private and derive ownership from verified identity.
7. Expose only modules whose data and persistence paths are ready for the authenticated workspace.

## Current release scope

The Google-authenticated workspace currently exposes:

- Overview and Upload Data
- Product Analytics
- Voice of Customer
- AI Analyst / document retrieval
- Product Opportunities
- Cohorts and Segments
- Funnels and Journeys
- Anomaly Detection
- Churn Prediction

Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer are intentionally hidden from Google workspaces pending completion of their tenant-owned persistence and isolation paths.

## Technical architecture

- Frontend: React, TypeScript, Vite and Recharts.
- API: Python, FastAPI and Pandas.
- Identity: Supabase Auth with Google OAuth and PKCE.
- API authentication: Supabase JWT verification using JWKS.
- Tenant persistence: Supabase PostgreSQL with RLS.
- Dataset storage: private Supabase Storage with owner-scoped paths and policies.
- Analytics / ML: NumPy, Pandas and scikit-learn.
- Hosting: Render for frontend/API and Supabase for identity and durable tenant data.

See [architecture.md](architecture.md), [multi-tenant-google-auth-plan.md](multi-tenant-google-auth-plan.md) and [demo-guide.md](demo-guide.md).

## Current non-goals

PulseOS is not positioned as an enterprise production analytics service. The current release does not claim full tenant migration of every legacy module, formal security certification, billing, enterprise RBAC, audit logging, OCR for scanned PDFs, generative AI answers or autonomous causal inference.
