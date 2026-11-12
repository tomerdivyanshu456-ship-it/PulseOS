# PulseOS

**AI-powered Product Intelligence Platform** for customer feedback analysis, product analytics, user behaviour insights, opportunity discovery, and experiment intelligence.

PulseOS is a portfolio-grade, locally runnable SaaS-style MVP for Product Analyst, AI Product Manager, and Associate Product Manager roles.

## MVP scope

- **Product analytics:** KPIs, conversion funnels, cohorts, retention, engagement, and feature adoption from behavioural event data.
- **Voice of Customer:** review sentiment and complaint-theme analysis from a separate customer review dataset.
- **AI Analyst:** constrained, evidence-backed questions, cross-source investigation recommendations, and explicit evidence limitations.
- **Product Opportunity Detection:** maps customer complaint themes to related behavioural signals using transparent keyword heuristics.
- **Experiment Intelligence:** turns opportunities into editable hypotheses, defines primary/secondary/guardrail metrics, designs a simple A/B test, estimates sample size and duration, tracks experiments in SQLite, compares observed control/variant results, and generates event-backed Ship / Iterate / Stop recommendations.
- **AI Product Strategy & Insights:** synthesises existing opportunity, customer, behavioural and experiment evidence into a ranked investigation roadmap, with transparent impact/confidence/effort scoring, editable effort estimates, recommended actions and success metrics. The module is deterministic and runs without a paid LLM API.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Recharts |
| Backend | Python 3.11, FastAPI |
| Database | SQLite |
| Analytics | Pandas, NumPy, scikit-learn |
| NLP | Lightweight CPU-friendly sentiment and topic tooling |
| Tests | Pytest, HTTPX |

No paid API keys, GPU, Docker, or additional infrastructure are required for the local MVP.

## Repository structure

```text
PulseOS/
├── frontend/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── docs/
└── README.md
```

## Dataset sources

1. **Retailrocket E-commerce Dataset** — behavioural events (views, add-to-cart, transactions): [Kaggle](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)
2. **Amazon Reviews 2023** — separate review data for Voice of Customer analysis: [Hugging Face](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
3. **Yelp Review Full** — alternative review benchmark: [Hugging Face](https://huggingface.co/datasets/Yelp/yelp_review_full)

These are independent sources. Do not join unrelated review records to Retailrocket user or transaction identifiers.

For an 8 GB RAM laptop, begin with 100k–200k event rows and 5k–10k review rows. Use chunked CSV processing where needed. Keep raw datasets out of Git.

## Local setup

### Prerequisites

- Python 3.11
- Node.js LTS
- Git

### Backend (PowerShell)

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

### Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

### Run backend tests

From the `backend` directory:

```powershell
python -m pytest
```

### Build the frontend

From the `frontend` directory:

```powershell
npm run build
```

## Experiment Intelligence methodology

- Hypotheses are generated from existing product-opportunity themes and are starting points for product investigation, not established explanations.
- Customer-review and behavioural datasets remain separate. Theme-level matching does not link an individual review to a user or session and is not causal evidence.
- The sample-size estimator uses a normal approximation for two independent binary proportions, a two-sided confidence level, specified power, and equal 50/50 allocation. It assumes independent eligible users and one preselected primary metric.
- Duration is a rough planning estimate based on total eligible daily traffic. Plan for at least one complete weekly cycle and account for ramp-up, seasonality, instrumentation quality, and exclusions.
- Result analysis reports observed arm rates, Wilson intervals for each arm, and an approximate unpooled interval for the difference. It is descriptive and does not replace a pre-registered statistical analysis or prove causality.
- Guardrail comparisons use user-entered rates and thresholds. They are review flags, not automatic rollout decisions.
- Event-backed decisions require explicit experiment exposure rows tagged with the saved experiment ID and an `experiment_variant` value of `control` or `variant`. The configured exposure event defines the eligible-user denominator; conversion and optional guardrail events are counted once per exposed user only when they occur at or after exposure.
- The decision rules recommend **Ship** only when both arms reach the planned sample, the approximate primary-metric difference interval is entirely positive, and at least one configured guardrail threshold is not exceeded; **Stop** when the interval is entirely negative or a configured guardrail threshold is exceeded; otherwise **Iterate**. Guardrail thresholds are screening flags, not statistical tests.
- The event-backed workflow assumes stable user-level assignment and complete instrumentation. It is a decision aid, not proof of causality or an automated deployment action.

### Event tracking contract for experiment decisions

The latest uploaded events CSV must retain the standard `user_id`, `event_name`, and `timestamp` columns and include two additional columns:

| Column | Purpose |
|---|---|
| `experiment_id` | Saved PulseOS experiment ID, populated on exposure rows |
| `experiment_variant` | `control` or `variant`, populated on exposure rows |

Each eligible user must have one tagged exposure event (default event name: `experiment_exposed`). The primary conversion event (default: `purchase`) must use the same `user_id` and occur at or after exposure. Configured guardrail events are also counted per exposed user; at least one guardrail event is required before a Ship recommendation is possible. Users with conflicting control/variant exposure assignments are excluded and reported. Existing event datasets without experiment tags continue to work for the other PulseOS analytics features, but cannot power event-backed experiment decisions.

## Data integrity principles

- Calculate displayed metrics from source data; do not hardcode production KPIs.
- Label demo data clearly.
- Show source, sample size, definitions, and assumptions for every metric.
- Keep behavioural events and third-party reviews analytically separate.
- Distinguish observed metrics, heuristic prioritisation, and causal evidence.
- Define one primary experiment metric before launch; monitor guardrails and avoid stopping early based on interim results.
- Document limitations and avoid unsupported causal claims.

## Project status

**Working MVP in active development.** Implemented CSV ingestion, behavioural product metrics, conversion funnels, weekly retention cohorts, repeat-usage metrics, event adoption, Voice of Customer analysis, evidence-backed AI Analyst, cross-source product opportunity detection, Experiment Intelligence planning/tracking/result analysis with event-backed decision recommendations, and an evidence-led Product Strategy & Insights roadmap.


## AI Product Strategy & Insights methodology

- The strategy workspace reuses PulseOS product opportunities and saved experiments; it does not create a second source of truth.
- Each recommendation includes customer evidence, any available theme-level behavioural signal, a recommended investigation action, a success metric and linked experiment coverage.
- Impact score is a heuristic: 60% customer complaint severity, 25% relative behavioural reach among the current opportunities, and 15% existing opportunity priority.
- Evidence confidence is based on the existing opportunity engine's review-volume evidence-strength score. It is not a statistical confidence interval.
- Priority score = impact score × evidence confidence × (3 ÷ effort estimate). Effort is adjustable from 1 (very low) to 5 (very high); changing it re-ranks the roadmap.
- The expected metric and success measurement are suggested validation criteria, not guaranteed outcomes. No revenue uplift or causal impact is inferred.
- Reviews and behavioural events are not joined at user/session level. Theme matching is hypothesis generation only.
- The module is deterministic and local-first; no paid LLM API, GPU or external inference service is required.
