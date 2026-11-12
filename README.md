# PulseOS

**Local-first Product Intelligence Platform** that helps product teams move from behavioural data and customer feedback to prioritised investigations and experiment decisions.

PulseOS is a portfolio project built around a practical product workflow: **measure product health → understand customer friction → find opportunities → investigate likely causes → design and evaluate experiments.**

> **Demo data notice:** The files in \`data/sample_*.csv\` are synthetic examples created for demonstrating the application. They are not real customer records and should not be interpreted as actual business performance.

## Product capabilities

| Workspace | What it helps answer |
|---|---|
| **Overview & Product Analytics** | How are active users, conversion, revenue, funnels and retention changing in the uploaded data? |
| **Voice of Customer** | What are customers complaining about, and how does review sentiment distribute? |
| **AI Analyst** | What evidence in the available datasets supports an analytical question, including passages retrieved from the active PDF/DOCX? |
| **Product Opportunities** | Which customer complaint themes may warrant behavioural investigation? |
| **Feature Intelligence** | Which features are being adopted and reused? |
| **Experiment Intelligence** | How should a hypothesis, primary metric, guardrails and test plan be defined? |
| **Experiment Decision Intelligence** | Given tagged exposure and outcome events, should a test be shipped, iterated or stopped? |
| **Strategy & Insights** | Which investigations should be prioritised, considering impact, evidence and effort? |
| **Product Health Scorecard** | What does the available evidence say about engagement, conversion, sentiment and experiment coverage? |
| **Cohort & Segments** | How do engagement and purchasing metrics differ across user attributes? |
| **Funnel & Journeys** | Where do users drop off in an ordered journey, and what paths do they take? |
| **Root Cause Explorer** | Which funnel, feedback and segment signals are worth investigating first? |
| **Anomaly Detection** | Which daily product activity metrics are unusual relative to recent history? |
| **Customer Churn Prediction** | Which behavioural patterns distinguish users who become inactive in a defined follow-up window? |

The platform is designed as decision support. It distinguishes observed metrics, heuristic rankings and experimental evidence rather than presenting correlations or keyword matches as proven causes.

## Document retrieval (local RAG foundation)

- PDF and DOCX uploads are text-extracted and stored locally.
- The AI Analyst searches only the currently selected Documents source.
- Retrieval prefers local semantic embeddings from \`sentence-transformers/all-MiniLM-L6-v2\`, using cosine similarity over normalized sentence embeddings.
- Semantic search is optional. If the dependency or model cannot load, PulseOS falls back to the existing TF-IDF unigram/bigram cosine retrieval. Set \`PULSEOS_SEMANTIC_SEARCH=false\` to force the lexical path.
- The model runs on CPU and is cached in-process. Its weights are downloaded once on first use (internet is required for that initial download); subsequent inference is local. No API key or paid service is used.
- The Analyst creates an extractive answer by selecting relevant source lines verbatim, with document filename and chunk-level citations. Section questions (such as "describe the experience section") attempt to return the named section rather than unrelated passages.
- This is not a generative LLM: answers are not paraphrased or expanded, and the system does not invent missing details. If no source line matches, it reports insufficient evidence.
- The current extraction pipeline does not preserve PDF page offsets, so citations use chunk numbers. Scanned PDFs without embedded text are not searchable because OCR is not enabled.
- Retrieval scores indicate semantic or lexical relevance, not confidence, truth or causal evidence.

### Optional semantic-search installation

The default installation remains lightweight and works without semantic dependencies. To enable MiniLM semantic retrieval in the backend virtual environment:

\`\`\`powershell
pip install -r requirements-semantic.txt
\`\`\`

The first semantic query downloads model weights. For an 8 GB CPU-only laptop, use the bounded batch size configured by PulseOS and close unnecessary applications during the first load. To force TF-IDF only:

\`\`\`powershell
$env:PULSEOS_SEMANTIC_SEARCH = "false"
\`\`\`

## Technology

- **Frontend:** React 19, TypeScript, Vite, Recharts
- **Backend:** Python, FastAPI, Pandas
- **Storage:** SQLite
- **Analytics / ML:** NumPy, scikit-learn, TF-IDF/KMeans, Isolation Forest, Logistic Regression and Random Forest
- **Optional semantic retrieval:** Sentence Transformers, PyTorch and all-MiniLM-L6-v2 (CPU)
- **Tests:** Pytest

**Local-first constraints:** no paid API keys, GPU, Docker or hosted inference service required. Semantic model weights are cached locally after the initial download.

## Architecture

\`\`\`text
CSV uploads
   │
   ▼
FastAPI ingestion + validation
   │
   ├── Behavioural events ──► Analytics / cohorts / funnels / segments
   │                              │
   │                              ▼
   │                       Opportunities / diagnostics
   │                              │
   │                              ▼
   │                       Strategy / experiments
   │
   └── Customer reviews ───► Sentiment / complaint themes
                                  │
                                  └── Theme-level opportunity signals

React + TypeScript workspace ◄──── JSON API
SQLite stores dataset metadata and experiment records;
uploaded CSV files are stored locally.
\`\`\`

Customer reviews and behavioural events are separate sources. PulseOS does not join unrelated third-party review records to individual user or session IDs.

## Repository structure

\`\`\`text
PulseOS/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-semantic.txt
├── frontend/
│   └── src/
├── data/
│   ├── raw/                 # Local uploads; not committed
│   ├── processed/
│   ├── sample_user_events.csv
│   ├── sample_churn_events.csv
│   └── sample_customer_reviews.csv
├── docs/
└── README.md
\`\`\`

## Run locally

### Prerequisites

- Python 3.11+
- Node.js LTS
- Git

### 1. Clone the repository

\`\`\`powershell
git clone https://github.com/tomerdivyanshu456-ship-it/PulseOS.git
cd PulseOS
\`\`\`

### 2. Start the backend

\`\`\`powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
# Optional: enable CPU-based semantic document search
pip install -r requirements-semantic.txt
uvicorn app.main:app --reload
\`\`\`

API documentation: http://127.0.0.1:8000/docs

### 3. Start the frontend

Open a second PowerShell terminal:

\`\`\`powershell
cd frontend
npm install
npm run dev
\`\`\`

Open http://localhost:5173.

### 4. Load the included demo CSVs

In the app, open **Upload Data** and upload:

- \`data/sample_user_events.csv\` as the behavioural events dataset for core analytics.
- \`data/sample_customer_reviews.csv\` as the customer reviews dataset.
- \`data/sample_churn_events.csv\` as the behavioural events dataset for Churn Prediction (14 days of synthetic history).

The synthetic event datasets include user, event, timestamp, session, product and categorical attributes (platform, plan, region and acquisition channel). The churn-specific file includes a constructed historical inactivity outcome for demonstration; do not interpret its labels or model metrics as real customer behaviour. The review dataset contains ratings, review text, dates and product categories.

For event-backed experiment decisions, use a separate experiment dataset with the exposure fields described below; the general demo events file is not tagged as an experiment.

## CSV contracts

### Behavioural events

Required columns:

| Column | Required | Description |
|---|---:|---|
| \`user_id\` | Yes | Stable user identifier |
| \`event_name\` | Yes | Event/action name |
| \`timestamp\` | Yes | Parseable event timestamp |
| \`session_id\` | No | Session identifier; enables session-level journey analysis |
| \`revenue\` | No | Revenue value on purchase events |
| Other categorical columns | No | Can be used for segment comparisons |

### Customer reviews

Required columns:

| Column | Required | Description |
|---|---:|---|
| \`review_id\` | Yes | Review identifier |
| \`rating\` | Yes | Numeric rating from 1 to 5 |
| \`review_text\` | Yes | Review text |

Optional fields such as \`review_date\` and \`product_category\` are useful for filtering and context.

### Experiment decision events

To analyse an experiment using event-level outcomes, include:

| Column | Purpose |
|---|---|
| \`experiment_id\` | Saved PulseOS experiment identifier on exposure rows |
| \`experiment_variant\` | \`control\` or \`variant\` on exposure rows |

Each eligible user needs a tagged exposure event (default: \`experiment_exposed\`). The primary conversion event (default: \`purchase\`) must share the same \`user_id\` and occur at or after exposure. Conflicting variant assignments are excluded and reported.

## Analytical methodology and limitations

- **Descriptive metrics:** calculated from the uploaded event window. DAU is distinct active users on the latest recorded calendar day; MAU uses the available 30-day window.
- **Funnel analysis:** configurable ordered funnel steps. When \`session_id\` exists, session-level units are used; otherwise analysis falls back to user-level units. This is not automatically a causal attribution model.
- **Segments:** categorical dimensions are assigned to each user using their most frequently observed non-empty value (alphabetical tie-break). Segment comparisons are descriptive.
- **Retention:** cohort and return-activity definitions are based on observed event dates and should be interpreted with the dataset's observation window in mind.
- **Voice of Customer:** lightweight text/sentiment and complaint-theme methods are useful for triage, not substitutes for human qualitative research or a validated language model.
- **Opportunity matching:** complaint themes and behavioural signals are matched at theme level. They are not linked at individual customer level.
- **Root Cause Explorer:** ranks diagnostic hypotheses from observed funnel, review-theme and segment signals. These are investigation leads, not proven root causes.
- **Health scorecard:** the overall index averages available pillars only; missing pillars are not treated as zero. Starter thresholds are illustrative defaults, not industry benchmarks.
- **Experiment planning:** sample-size estimates use a normal approximation for two independent binary proportions, two-sided confidence, specified power and equal allocation. Duration estimates are planning approximations.
- **Experiment decisions:** observed arm rates and approximate confidence intervals support a Ship / Iterate / Stop recommendation. Instrumentation, stable assignment, adequate sample size and guardrails matter; this is not proof of causality or an automated deployment action.
- **Strategy scoring:** impact, evidence confidence and effort are transparent heuristics for prioritisation, not predicted business outcomes.
- **Anomaly detection:** independent Isolation Forest models flag unusual daily metrics; contamination is a modelling assumption and flags are not proof of incidents.
- **Churn prediction:** churn is operationalised as no recorded event in the 7 calendar days after a 7-day observation window. User-level features use only the observation window; a stratified holdout evaluates Logistic Regression and Random Forest. This is an inactivity proxy, not confirmed cancellation, and holdout scores are retrospective rather than live customer risk predictions.

## Quality checks

Run backend tests from \`backend/\`:

\`\`\`powershell
python -m pytest -q
\`\`\`

Build the frontend from \`frontend/\`:

\`\`\`powershell
npm.cmd run build
\`\`\`

## Project status

PulseOS is a working local MVP with CSV ingestion, product analytics, customer feedback analysis, evidence-backed analysis workflows, cohort/segment and journey intelligence, experiment planning and event-backed decision support. It is intended as a demonstrable product analytics and product decision-support portfolio project; it is not positioned as a production multi-tenant SaaS or an autonomous causal inference system.
