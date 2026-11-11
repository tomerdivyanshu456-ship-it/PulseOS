# PulseOS

**AI-powered Product Intelligence Platform** for customer feedback analysis, product analytics, user behaviour insights, and experimentation.

PulseOS is being built as a portfolio-grade, locally runnable SaaS-style MVP for Product Analyst, AI Product Manager, and Associate Product Manager roles.

## MVP scope

- Product analytics from behavioural event data: KPIs, funnels, cohorts, and retention.
- Voice of Customer analysis from a separate review dataset: sentiment and topic discovery.
- A constrained, evidence-backed analytical question interface.
- A/B experiment analysis as a follow-on module.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | SQLite |
| Analytics | Pandas, NumPy, scikit-learn |
| NLP | TF-IDF + lightweight sentiment tooling; optional small CPU model |
| Tests | Pytest, HTTPX |

No paid API keys or GPU are required for the planned MVP.

## Repository structure

```text
PulseOS/
├── frontend/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── data/
│   ├── raw/
│   └── processed/
├── docs/
├── .gitignore
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
- VS Code (recommended editor)

### Backend (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

## 14-day MVP roadmap

| Days | Deliverable |
|---|---|
| 1–2 | Setup, API health check, React-to-FastAPI connection |
| 3 | SQLite schema and CSV ingestion |
| 4–5 | Product KPIs and conversion funnel |
| 6 | Cohort and retention analysis |
| 7 | Overview dashboard |
| 8–10 | Review preprocessing, sentiment, topic discovery |
| 11 | Voice of Customer interface |
| 12 | Constrained analytical question engine |
| 13 | Tests and deployment attempt |
| 14 | Documentation, demo, and polish |

## Data integrity principles

- Calculate displayed metrics from source data; do not hardcode production KPIs.
- Label demo data clearly.
- Show source, sample size, definitions, and assumptions for every metric.
- Keep behavioural events and third-party reviews analytically separate.
- Document limitations and avoid unsupported causal claims.

## Project status

**Initial repository scaffold.** Implementation is starting with the backend health endpoint and frontend connection.
