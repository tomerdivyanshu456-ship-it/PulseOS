# PulseOS

**AI-powered Product Intelligence Platform** for customer feedback analysis, product analytics, user behaviour insights, opportunity discovery, and experiment intelligence.

PulseOS is a portfolio-grade, locally runnable SaaS-style MVP for Product Analyst, AI Product Manager, and Associate Product Manager roles.

## MVP scope

- **Product analytics:** KPIs, conversion funnels, cohorts, retention, engagement, and feature adoption from behavioural event data.
- **Voice of Customer:** review sentiment and complaint-theme analysis from a separate customer review dataset.
- **AI Analyst:** constrained, evidence-backed questions, cross-source investigation recommendations, and explicit evidence limitations.
- **Product Opportunity Detection:** maps customer complaint themes to related behavioural signals using transparent keyword heuristics.
- **Experiment Intelligence:** turns opportunities into editable hypotheses, defines primary/secondary/guardrail metrics, designs a simple A/B test, estimates sample size and duration, tracks experiments in SQLite, and compares observed control/variant results.

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

## Data integrity principles

- Calculate displayed metrics from source data; do not hardcode production KPIs.
- Label demo data clearly.
- Show source, sample size, definitions, and assumptions for every metric.
- Keep behavioural events and third-party reviews analytically separate.
- Distinguish observed metrics, heuristic prioritisation, and causal evidence.
- Define one primary experiment metric before launch; monitor guardrails and avoid stopping early based on interim results.
- Document limitations and avoid unsupported causal claims.

## Project status

**Working MVP in active development.** Implemented CSV ingestion, behavioural product metrics, conversion funnels, weekly retention cohorts, repeat-usage metrics, event adoption, Voice of Customer analysis, evidence-backed AI Analyst, cross-source product opportunity detection, and Experiment Intelligence planning/tracking/result analysis.
