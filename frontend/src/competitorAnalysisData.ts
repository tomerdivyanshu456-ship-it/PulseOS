export const mixpanelVerifiedDate = "2026-11-20";

const docs = "https://docs.mixpanel.com/docs";

export const mixpanelSources = {
  product: { label: "Product overview", url: `${docs}/what-is-mixpanel` },
  insights: { label: "Insights", url: `${docs}/reports/insights` },
  tracking: { label: "Tracking methods", url: `${docs}/tracking-methods` },
  funnels: { label: "Funnels configuration", url: `${docs}/reports/funnels/funnels-advanced` },
  cohorts: { label: "Cohorts", url: `${docs}/users/cohorts` },
  retention: { label: "Retention", url: `${docs}/reports/retention` },
  flows: { label: "Flows", url: `${docs}/reports/flows` },
  replay: { label: "Session Replay", url: "https://mixpanel.com/platform/session-replay/" },
  feedback: { label: "Survicate integration", url: "https://mixpanel.com/partners/integrations/survicate" },
  monitoring: { label: "Monitoring & alerts", url: "https://mixpanel.com/pricing/" },
  churn: { label: "Churn analytics", url: "https://mixpanel.com/blog/churn-analytics/" },
  context: { label: "MCP connections", url: `${docs}/mcp-connections` },
  agent: { label: "Mixpanel Agent", url: `${docs}/mixpanel-agent` },
  roles: { label: "Roles & permissions", url: `${docs}/orgs-and-projects/roles-and-permissions` },
  access: { label: "Data views & classification", url: `${docs}/data-governance/data-views-and-classification` },
};

export const availabilityLabels = {
  available: "Available",
  partial: "Partially Available",
  unavailable: "Not Available",
  unverified: "Needs Verification",
};

export const evidenceLabels = {
  verified: "Verified in official documentation",
  inferred: "Inferred from official documentation",
  unverified: "Native capability unconfirmed",
};

export type Availability = keyof typeof availabilityLabels;

type Capability = { status: Availability; detail: string };
type Comparison = {
  capability: string;
  mixpanel: Capability & {
    evidence: keyof typeof evidenceLabels;
    source: keyof typeof mixpanelSources;
  };
  pulseos: Capability;
  comparison: string;
};

export const comparisons: Comparison[] = [
  {
    capability: "Product analytics",
    mixpanel: { status: "available", detail: "Insights reports measure and break down event trends.", evidence: "verified", source: "insights" },
    pulseos: { status: "available", detail: "Product Analytics reports activity, conversion, feature adoption and retention from imported events." },
    comparison: "Mixpanel offers more control over the metrics and breakdowns product managers build.",
  },
  {
    capability: "Event tracking",
    mixpanel: { status: "available", detail: "Offers SDKs, autocapture and other documented ingestion methods.", evidence: "verified", source: "tracking" },
    pulseos: { status: "unavailable", detail: "Upload Data imports existing CSV or XLSX event records. In-app event collection is outside its scope." },
    comparison: "Mixpanel supports ongoing capture from instrumented products. PulseOS analyses imported snapshots.",
  },
  {
    capability: "Funnel analysis",
    mixpanel: { status: "available", detail: "Supports step-level filters, conversion windows and ordering controls.", evidence: "verified", source: "funnels" },
    pulseos: { status: "available", detail: "Funnel & Journeys builds ordered funnels of two to six events with drop-off and segment comparisons." },
    comparison: "Both show conversion and drop-off. Mixpanel supports more ways to define a conversion.",
  },
  {
    capability: "Cohort analysis",
    mixpanel: { status: "available", detail: "Builds reusable cohorts with event and property conditions.", evidence: "verified", source: "cohorts" },
    pulseos: { status: "partial", detail: "Product Analytics groups users by first observed week for retention. Cohort & Segments compares groups from available dimensions." },
    comparison: "Mixpanel lets teams define and reuse behavioural cohorts across reports.",
  },
  {
    capability: "User segmentation",
    mixpanel: { status: "available", detail: "Filters and breaks down reports by properties and cohorts.", evidence: "verified", source: "insights" },
    pulseos: { status: "available", detail: "Cohort & Segments compares users across dimensions found in the active event data." },
    comparison: "Mixpanel has more flexible filters. PulseOS works with the dimensions present in the upload.",
  },
  {
    capability: "Retention analysis",
    mixpanel: { status: "available", detail: "Measures return behaviour using selected events and time intervals.", evidence: "verified", source: "retention" },
    pulseos: { status: "available", detail: "Product Analytics shows repeat weekly activity by first-seen cohort when enough history is available." },
    comparison: "Mixpanel can measure repeat use of specific actions. PulseOS uses a weekly activity definition.",
  },
  {
    capability: "User journeys",
    mixpanel: { status: "available", detail: "Flows explores paths into and out of selected events.", evidence: "verified", source: "flows" },
    pulseos: { status: "available", detail: "Funnel & Journeys shows common observed event sequences, capped at six events." },
    comparison: "Mixpanel helps investigate paths around a selected event. PulseOS summarises the most common sequences in an upload.",
  },
  {
    capability: "Customer feedback analysis",
    mixpanel: { status: "partial", detail: "Its directory documents an external survey integration that sends responses into Mixpanel.", evidence: "inferred", source: "feedback" },
    pulseos: { status: "available", detail: "Voice of Customer analyses uploaded review text and surfaces customer pain points and examples." },
    comparison: "PulseOS includes an uploaded-review workflow. The documented Mixpanel survey workflow uses a partner tool.",
  },
  {
    capability: "Sentiment analysis",
    mixpanel: { status: "unverified", detail: "The survey integration describes partner-side text analysis. Native review sentiment scoring is unconfirmed.", evidence: "unverified", source: "feedback" },
    pulseos: { status: "available", detail: "Voice of Customer assigns rule-based sentiment to uploaded reviews." },
    comparison: "PulseOS surfaces review sentiment directly in its feedback module.",
  },
  {
    capability: "Review clustering",
    mixpanel: { status: "unverified", detail: "The survey integration describes partner-side topic categorisation. Native review clustering is unconfirmed.", evidence: "unverified", source: "feedback" },
    pulseos: { status: "available", detail: "Voice of Customer groups similar review text with TF-IDF and K-means when enough reviews are available." },
    comparison: "PulseOS provides a dedicated review-theme clustering workflow.",
  },
  {
    capability: "Anomaly detection",
    mixpanel: { status: "available", detail: "Mixpanel documents anomaly detection and metric alerts. Availability varies by plan.", evidence: "verified", source: "monitoring" },
    pulseos: { status: "available", detail: "Anomaly Detection flags unusual daily product metrics in the active event dataset." },
    comparison: "Mixpanel offers alerting on monitored metrics. PulseOS surfaces findings during analysis of the uploaded history.",
  },
  {
    capability: "Churn prediction",
    mixpanel: { status: "unverified", detail: "Mixpanel documents churn analysis and rule-defined at-risk cohorts. A native predictive model is unconfirmed.", evidence: "unverified", source: "churn" },
    pulseos: { status: "available", detail: "Churn Prediction trains and evaluates models on eligible event data using a retrospective churn definition." },
    comparison: "PulseOS exposes model evaluation for uploaded data. The documented Mixpanel workflow analyses churn behaviour.",
  },
  {
    capability: "Document ingestion",
    mixpanel: { status: "unverified", detail: "Mixpanel Agent can read context through connectors. Native PDF or DOCX upload and passage retrieval are unconfirmed.", evidence: "unverified", source: "context" },
    pulseos: { status: "available", detail: "Upload Data accepts PDFs and DOCX files. AI Analyst retrieves relevant passages from the active document." },
    comparison: "PulseOS can ground a product question in passages from an uploaded document.",
  },
  {
    capability: "AI-assisted product insights",
    mixpanel: { status: "available", detail: "Mixpanel Agent can run analyses, build reports, create cohorts and investigate replays.", evidence: "verified", source: "agent" },
    pulseos: { status: "available", detail: "AI Analyst answers supported product questions using local analytics, feedback and document evidence." },
    comparison: "Mixpanel’s assistant works across its analytics tools. PulseOS focuses on evidence in the active data sources.",
  },
  {
    capability: "Feedback and behavioural data integration",
    mixpanel: { status: "partial", detail: "An external integration sends survey responses as events and user properties for analysis alongside product events.", evidence: "inferred", source: "feedback" },
    pulseos: { status: "partial", detail: "Opportunities matches event names and review themes at the feature level. It does not link individual users or sessions." },
    comparison: "Mixpanel can analyse integrated survey responses by user. PulseOS combines separate uploads to generate investigation leads.",
  },
  {
    capability: "Shared multi-user workspaces",
    mixpanel: { status: "available", detail: "Multiple team members can be invited into projects with assigned roles.", evidence: "verified", source: "roles" },
    pulseos: { status: "unavailable", detail: "Each Google account has a private workspace. Shared projects and member invitations are outside the current scope." },
    comparison: "Mixpanel lets teammates collaborate on the same project. PulseOS isolates each user's workspace.",
  },
  {
    capability: "Data access controls",
    mixpanel: { status: "available", detail: "Project data views and classification can restrict which data a team can access.", evidence: "verified", source: "access" },
    pulseos: { status: "partial", detail: "Workspace data is owner-scoped. Shared-project roles and fine-grained team permissions are outside the current scope." },
    comparison: "Mixpanel controls access within a shared project. PulseOS enforces boundaries between private owners.",
  },
  {
    capability: "Session replay",
    mixpanel: { status: "available", detail: "Session Replay links recordings to analytics workflows. Heatmaps summarise interaction patterns.", evidence: "verified", source: "replay" },
    pulseos: { status: "unavailable", detail: "The journey view uses event records. PulseOS does not record or replay sessions." },
    comparison: "Mixpanel can show the interface interactions behind a funnel drop-off.",
  },
];

export const mixpanelStrengths = [
  { title: "Flexible event reporting", detail: "Start from instrumented events, then break down product metrics by event or user properties.", sources: [mixpanelSources.insights] },
  { title: "Conversion and retention", detail: "Set funnel steps and conversion windows, then measure whether users return to specific actions.", sources: [mixpanelSources.funnels, mixpanelSources.retention] },
  { title: "Reusable segments", detail: "Create behavioural cohorts and reuse them when comparing conversion, retention and other metrics.", sources: [mixpanelSources.cohorts] },
  { title: "From reports to individual sessions", detail: "Use Flows to explore common paths and Session Replay to inspect interaction friction in individual sessions.", sources: [mixpanelSources.flows, mixpanelSources.replay] },
];

export const pulseosDifferentiators = [
  { title: "Voice of Customer from uploaded reviews", detail: "Surface feedback themes, rule-based sentiment and machine-learning review clusters in Voice of Customer." },
  { title: "Feature-level opportunity discovery", detail: "Bring behavioural counts and review evidence together in Opportunities to decide what deserves investigation." },
  { title: "Evidence from product documents", detail: "Upload a PDF or DOCX and use AI Analyst to find passages from the active document alongside the other workspace tools." },
];

type Gap = {
  title: string;
  priority: "High" | "Medium" | "Low";
  reason: string;
  impact: string;
  improvement: string;
};

export const productGaps: Gap[] = [
  {
    title: "Ongoing event collection", priority: "High",
    reason: "Conversion and retention depend on consistent, time-stamped event history.",
    impact: "Teams repeat exports and may make decisions from stale snapshots.",
    improvement: "Evaluate an authenticated event ingestion endpoint with a documented schema and deduplication.",
  },
  {
    title: "Shared projects and member roles", priority: "High",
    reason: "Teams need a common view of evidence with clear responsibility for access.",
    impact: "Colleagues cannot review the same workspace data from separate accounts.",
    improvement: "Design project invitations and viewer/editor roles with project-scoped data policies.",
  },
  {
    title: "Configurable retention and saved cohorts", priority: "Medium",
    reason: "Meaningful repeat activity depends on the product and lifecycle stage.",
    impact: "Teams have limited ways to compare custom segments and distinguish repeat feature use from general activity.",
    improvement: "Add selectable entry and return events, then allow cohort rules to be saved and reused.",
  },
  {
    title: "Funnel and path exploration", priority: "Medium",
    reason: "A meaningful conversion window and path anchor depend on the question being asked.",
    impact: "Teams have less control when investigating drop-off, delays or detours between steps.",
    improvement: "Evaluate conversion-window controls and allow common paths to be explored around a selected event.",
  },
  {
    title: "Proactive anomaly alerts", priority: "Medium",
    reason: "Metric changes can matter before the next manual review.",
    impact: "Teams see flagged dates only when they analyse the uploaded history.",
    improvement: "Assess opt-in notifications for selected metrics once event data can be refreshed consistently.",
  },
  {
    title: "Session replay for friction research", priority: "Low",
    reason: "Event paths show the sequence of actions, while recordings can reveal the interaction behind it.",
    impact: "Teams may need interviews or separate recordings to explain why users get stuck.",
    improvement: "Validate demand and privacy requirements before considering a suitably masked replay integration.",
  },
];
