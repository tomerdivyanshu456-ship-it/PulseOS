# PulseOS live demo walkthrough

**Live app:** https://pulseos-frontend.onrender.com

This walkthrough is designed for a short recruiter or product interview demo.

## 1. Sign in

- Open the live app and choose Google sign-in.
- Complete OAuth.
- Confirm that the private workspace is ready.
- Refresh once to demonstrate that the authenticated session is restored.

## 2. Upload the sample data

From the repository, download:

- `data/sample_user_events.csv`
- `data/sample_customer_reviews.csv`

In **Upload Data**:

- Upload the event file as behavioural events.
- Upload the reviews file as customer reviews.
- Confirm each dataset appears in the workspace and is selected as active.

The included files are synthetic demo data, not real company data.

## 3. Explore Product Analytics

Open Product Analytics and explain how event-level records are converted into product metrics and behavioural views. Point out the observation window and the definitions/limitations shown by the product.

## 4. Explore Voice of Customer

Open Voice of Customer and inspect review ratings, sentiment and complaint themes. Explain that review themes help identify problems worth investigating; they are not automatically linked to individual event users.

## 5. Demonstrate tenant isolation

For a second-account demonstration:

1. Open an Incognito/private browser window.
2. Sign in with a different Google account.
3. Upload a different dataset.
4. Confirm that this account sees its own workspace and dataset list, not the first account's uploads.

The live smoke test also checked that the second account could not preview or delete the first account's dataset by substituting its ID.

## 6. Close with honest scope

Explain that the current Google workspace exposes the core analytics and feedback workflow. Experiments, Strategy & Insights, Health Scorecard and Root Cause Explorer remain hidden until their tenant-owned persistence paths are completed.

## Suggested 90-second narrative

"PulseOS is a product intelligence workspace I built to connect behavioural analytics with customer feedback. A user signs in with Google, gets a private workspace, uploads event and review data, and explores product metrics and customer themes. I focused on the data path as much as the interface: the API verifies Supabase JWTs, derives the owner from the verified identity, and uses Postgres RLS and private Storage policies for dataset isolation. I tested two separate accounts against upload, list, preview and delete operations. The analytics are decision support, so I distinguish observed metrics from heuristic signals and avoid claiming that correlation proves root cause. The current release deliberately exposes only the modules whose tenant data paths are ready."

## Demo checklist

- [ ] Live app opens.
- [ ] Google sign-in completes.
- [ ] Workspace is ready after refresh.
- [ ] Event CSV upload succeeds and becomes active.
- [ ] Review CSV upload succeeds and becomes active.
- [ ] Product Analytics shows event-based output.
- [ ] Voice of Customer shows review-based output.
- [ ] Second account sees a separate workspace.
- [ ] No real customer or confidential data is used.
