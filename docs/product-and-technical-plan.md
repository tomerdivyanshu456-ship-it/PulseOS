# PulseOS Product & Technical Plan

## Goal

Build a credible, locally runnable product intelligence MVP in 14 days with a zero-rupee API budget and an 8 GB RAM, CPU-only laptop.

## Target users

- **Product Analyst:** investigates activation, conversion, retention, and feature adoption.
- **Product Manager:** identifies customer problems, prioritises opportunities, and measures experiments.
- **AI Product Manager:** evaluates AI-assisted insight workflows with evidence and measurable outcomes.

## MVP acceptance criteria

1. User can inspect sample or uploaded behavioural event data.
2. Backend calculates documented KPIs and funnel steps from stored records.
3. Cohort and retention calculations disclose their definitions.
4. User can upload customer review text and ratings.
5. Sentiment and topic outputs disclose method, sample size, and limitations.
6. Analytical questions execute only through an allowlisted, read-only query layer.
7. Frontend provides loading, empty, validation, and error states.
8. Tests cover metric calculations and API contracts.

## Metric definitions to document

- **DAU:** distinct active users on a calendar day in the dataset timezone.
- **Funnel conversion:** users reaching the final step divided by users entering the first step, with a stated attribution window.
- **Retention:** cohort users with a qualifying activity event in a later period divided by cohort size.
- **Sentiment distribution:** successfully classified review count per class divided by all successfully processed reviews.

## 14-day schedule

- Days 1–2: setup and API connection.
- Day 3: SQLite schema and ingestion validation.
- Days 4–6: metrics, funnel, cohorts, and retention.
- Day 7: overview dashboard.
- Days 8–10: review preprocessing, sentiment, and topic discovery.
- Day 11: Voice of Customer interface.
- Day 12: constrained question engine.
- Day 13: tests and deployment attempt.
- Day 14: documentation, demo, and polish.

## Engineering guardrails

- No paid API dependency.
- No GPU dependency.
- Keep raw data local and out of Git.
- Process CSVs in chunks and cap initial sample sizes.
- Do not combine third-party reviews with unrelated behavioural user IDs.
- Do not present placeholder numbers as measured findings.
