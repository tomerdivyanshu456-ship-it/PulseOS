import { useEffect, useState, type FormEvent } from "react";

import {
  LayoutDashboard,
  BarChart3,
  MessageSquareText,
  Sparkles,
  FlaskConical,
  UploadCloud,
  Bell,
  Search,
  Users,
  TrendingUp,
  Activity,
  IndianRupee,
  Target,
  Lightbulb,
  Gauge,
  Route,
  AlertTriangle,
  UserMinus,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getAnalytics,
  getHealth,
  getAuthConfig,
  authenticate,
  clearAuth,
  getDatasets,
  getActiveDatasets,
  setActiveDataset,
  type UploadedDataset,
  type ActiveDatasetMap,
  type AnalyticsOverview,
} from "./services/api";
import UploadData from "./UploadData";
import ProductAnalytics from "./ProductAnalytics";
import ProductOpportunities from "./ProductOpportunities";
import VoiceOfCustomer from "./VoiceOfCustomer";
import AIAnalyst from "./AIAnalyst";
import ExperimentIntelligence from "./ExperimentIntelligence";
import ProductStrategy from "./ProductStrategy";
import ProductHealthScorecard from "./ProductHealthScorecard";
import CohortSegmentIntelligence from "./CohortSegmentIntelligence";
import FunnelJourneyIntelligence from "./FunnelJourneyIntelligence";
import RootCauseExplorer from "./RootCauseExplorer";
import ProductAnomalies from "./ProductAnomalies";
import CustomerChurn from "./CustomerChurn";
import "./App.css";
import "./Auth.css";
import "./PulseTheme.css";
import { completeGoogleSignIn, getGoogleUserEmail, isSupabaseAuthConfigured, startGoogleSignIn } from "./services/supabaseAuth";

const navigation = [
  { group: "WORKSPACE", name: "Overview", icon: LayoutDashboard },
  { group: "WORKSPACE", name: "Upload Data", icon: UploadCloud },
  { group: "UNDERSTAND", name: "Product Analytics", icon: BarChart3 },
  { group: "UNDERSTAND", name: "Cohort & Segments", icon: Users },
  { group: "UNDERSTAND", name: "Funnel & Journeys", icon: Route },
  { group: "UNDERSTAND", name: "Voice of Customer", icon: MessageSquareText },
  { group: "INTELLIGENCE", name: "AI Analyst", icon: Sparkles },
  { group: "INTELLIGENCE", name: "Opportunities", icon: Target },
  { group: "INTELLIGENCE", name: "Root Cause Explorer", icon: Search },
  { group: "INTELLIGENCE", name: "Anomaly Detection", icon: AlertTriangle },
  { group: "OPTIMIZE", name: "Experiments", icon: FlaskConical },
  { group: "OPTIMIZE", name: "Strategy & Insights", icon: Lightbulb },
  { group: "OPTIMIZE", name: "Health Scorecard", icon: Gauge },
  { group: "OPTIMIZE", name: "Churn Prediction", icon: UserMinus },
];

const numberFormatter = new Intl.NumberFormat("en-IN");
const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function App() {
  const [authState, setAuthState] = useState<"loading" | "unavailable" | "required" | "authenticated" | "disabled">("loading");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [status, setStatus] = useState("Connecting...");
  const [googleConfigured] = useState(isSupabaseAuthConfigured());
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleMessage, setGoogleMessage] = useState("");
  const [googleEmail, setGoogleEmail] = useState<string | null>(null);

  useEffect(() => {
    getAuthConfig()
      .then((config) => setAuthState(config.auth_required ? "required" : "disabled"))
      .catch(() => setAuthState("unavailable"));

    completeGoogleSignIn()
      .then((completed) => {
        if (completed) {
          setGoogleEmail(getGoogleUserEmail());
          setGoogleMessage("Google identity verified. Workspace access will be enabled after the secure account-isolation backend is deployed.");
        }
      })
      .catch((error: unknown) => setGoogleMessage(error instanceof Error ? error.message : "Google sign-in failed. Please try again."));
  }, []);

  async function handleGoogleLogin() {
    setGoogleLoading(true);
    setGoogleMessage("");
    try {
      await startGoogleSignIn();
    } catch (error) {
      setGoogleMessage(error instanceof Error ? error.message : "Could not start Google sign-in.");
      setGoogleLoading(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginLoading(true);
    setLoginError("");
    try {
      await authenticate(loginPassword);
      setLoginPassword("");
      setAuthState("authenticated");
    } catch {
      setLoginError("Sign-in failed. Check the password and try again.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    clearAuth();
    setLoginPassword("");
    setAuthState("required");
  }
  const [activePage, setActivePage] = useState("Overview");
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");
  const [datasets, setDatasets] = useState<UploadedDataset[]>([]);
  const [activeDatasets, setActiveDatasets] = useState<ActiveDatasetMap>({ events: null, reviews: null, documents: null });
  const emptyActiveDatasets: ActiveDatasetMap = { events: null, reviews: null, documents: null };
  const [sourceError, setSourceError] = useState("");

  async function refreshDataSources() {
    const [available, active] = await Promise.all([getDatasets(), getActiveDatasets()]);
    setDatasets(Array.isArray(available) ? available : []);
    setActiveDatasets(active && typeof active === "object" ? {
      events: active.events ?? null,
      reviews: active.reviews ?? null,
      documents: active.documents ?? null,
    } : emptyActiveDatasets);
  }

  useEffect(() => {
    if (authState !== "authenticated" && authState !== "disabled") return;
    const refresh = () => refreshDataSources().catch(() => setSourceError("Could not load active data sources."));
    refresh();
    window.addEventListener("pulseos:datasets-changed", refresh);
    return () => window.removeEventListener("pulseos:datasets-changed", refresh);
  }, [authState]);

  async function changeDataSource(kind: "events" | "reviews" | "documents", id: string) {
    const selected = id ? datasets.find((item) => item.id === id) || null : null;
    try {
      await setActiveDataset(kind, selected?.id || null);
      setActiveDatasets((current) => ({ ...current, [kind]: selected }));
      setAnalytics(null);
    } catch {
      setSourceError("Could not update the active data source.");
    }
  }

  const dataContextKey = [activeDatasets.events?.id || "none", activeDatasets.reviews?.id || "none", activeDatasets.documents?.id || "none"].join(":");

  useEffect(() => {
    if (authState !== "authenticated" && authState !== "disabled") return;
    getHealth()
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Offline"));
  }, [authState]);

  // Refresh when the user returns to Overview after uploading a dataset.
  useEffect(() => {
    if (authState !== "authenticated" && authState !== "disabled") return;
    if (activePage !== "Overview") return;

    let cancelled = false;
    setAnalyticsLoading(true);
    setAnalyticsError("");

    getAnalytics()
      .then((data) => {
        if (cancelled) return;
        // Do not let an incomplete or unexpected API payload crash the entire app.
        if (!data || !data.metrics || typeof data.metrics.daily_active_users !== "number") {
          setAnalytics(null);
          setAnalyticsError("The analytics API returned incomplete data. Upload and activate an events CSV, then refresh the Overview.");
          return;
        }
        setAnalytics(data);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setAnalytics(null);

        const message =
          typeof error === "object" &&
          error !== null &&
          "response" in error &&
          typeof error.response === "object" &&
          error.response !== null &&
          "data" in error.response &&
          typeof error.response.data === "object" &&
          error.response.data !== null &&
          "detail" in error.response.data &&
          typeof error.response.data.detail === "string"
            ? error.response.data.detail
            : error instanceof Error && error.message
              ? error.message
              : "Unable to load product analytics. Check that the backend is running.";

        setAnalyticsError(message);
      })
      .finally(() => {
        if (!cancelled) setAnalyticsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activePage, dataContextKey, authState]);

  const hasAnalytics = analytics !== null;
  const metrics = hasAnalytics
    ? [
        {
          title: "Daily Active Users",
          value: numberFormatter.format(analytics.metrics.daily_active_users),
          description: "Unique users on the latest recorded day",
          icon: Users,
        },
        {
          title: "Monthly Active Users",
          value: numberFormatter.format(analytics.metrics.monthly_active_users),
          description: "Unique users in the 30-day data window",
          icon: Activity,
        },
        {
          title: "Conversion Rate",
          value: `${analytics.metrics.conversion_rate.toFixed(2)}%`,
          description: "Purchasing users ÷ product viewers",
          icon: TrendingUp,
        },
        {
          title: "Total Revenue",
          value: currencyFormatter.format(analytics.metrics.total_revenue),
          description: "Revenue recorded on purchase events",
          icon: IndianRupee,
        },
      ]
    : [];

  if (authState === "loading") {
    return <main className="auth-screen"><div className="auth-card"><div className="auth-brand">Pulse<span>OS</span></div><p>Connecting to your workspace…</p></div></main>;
  }

  if (authState === "unavailable") {
    return <main className="auth-screen"><div className="auth-card"><div className="auth-brand">Pulse<span>OS</span></div><h1>Backend unavailable</h1><p>PulseOS could not load its authentication configuration. Check that the API is running, then refresh this page.</p></div></main>;
  }

  if (authState === "required") {
    return (
      <main className="auth-screen">
        <form className="auth-card" onSubmit={handleLogin}>
          <div className="auth-brand">Pulse<span>OS</span></div>
          <p className="auth-eyebrow">PRIVATE WORKSPACE</p>
          <h1>Sign in to PulseOS</h1>
          <p>Sign in to your product intelligence workspace.</p>
          {googleConfigured && <button className="google-signin-button" type="button" onClick={() => void handleGoogleLogin()} disabled={googleLoading}>
            <svg aria-hidden="true" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.76 7.18l7.73 6C44.42 38.05 46.98 31.88 46.98 24.55Z"/><path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.87.93 7.52 2.56 10.78l7.97-6.19Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.14 1.45-4.88 2.3-8.18 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"/></svg>
            {googleLoading ? "Redirecting to Google…" : "Continue with Google"}
          </button>}
          {googleEmail && <p className="auth-google-email">Signed in as {googleEmail}</p>}
          {googleMessage && <div className="auth-info" role="status">{googleMessage}</div>}
          {googleConfigured && <div className="auth-divider"><span>or use legacy administrator access</span></div>}
          <p className="auth-legacy-copy">Legacy administrator sign-in</p>
          <label htmlFor="pulseos-password">Administrator password</label>
          <input id="pulseos-password" type="password" autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} required autoFocus />
          {loginError && <div className="auth-error" role="alert">{loginError}</div>}
          <button type="submit" disabled={loginLoading || !loginPassword}>{loginLoading ? "Signing in…" : "Sign in"}</button>
        </form>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">P</div>
          <span>
            Pulse<span className="brand-light">OS</span>
          </span>
        </div>

        <nav aria-label="Main navigation">
          {navigation.map((item, index) => {
            const Icon = item.icon;
            const showGroup = index === 0 || item.group !== navigation[index - 1].group;
            return (
              <div className="nav-entry" key={item.name}>
                {showGroup && <p className="nav-group-label">{item.group}</p>}
                <button
                  className={`nav-item ${activePage === item.name ? "active" : ""}`}
                  onClick={() => setActivePage(item.name)}
                  aria-current={activePage === item.name ? "page" : undefined}
                >
                  <Icon size={18} />
                  <span>{item.name}</span>
                </button>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="connection">
            <span
              className={`status-dot ${status === "healthy" ? "" : "offline"}`}
            />
            <div>
              <strong>System status</strong>
              <small>{status}</small>
            </div>
          </div>

          <div className="profile">
            <div className="avatar">DT</div>
            <div>
              <strong>Workspace</strong>
              <small>Product Intelligence</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> {activePage}
          </div>
          <div className="top-actions">
            <div className="workspace-source-selectors">
              <button className="source-refresh-button" type="button" onClick={() => void refreshDataSources().catch(() => setSourceError("Could not refresh active data sources."))}>Refresh sources</button>
              {(["events", "reviews", "documents"] as const).map((kind) => (
                <label key={kind} className="workspace-source-picker">
                  <span>{kind}</span>
                  <select value={activeDatasets[kind]?.id || ""} onChange={(event) => void changeDataSource(kind, event.target.value)}>
                    <option value="">No active {kind}</option>
                    {datasets.filter((item) => item.dataset_type === kind).map((item) => (
                      <option key={item.id} value={item.id}>{item.original_filename}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <button className="icon-button" aria-label="Search">
              <Search size={19} />
            </button>
            <button className="icon-button" aria-label="Notifications">
              <Bell size={19} />
            </button>
            {authState === "authenticated" && <button className="auth-signout" type="button" onClick={handleLogout}>Sign out</button>}
            <div className="avatar small-avatar">DT</div>
          </div>
        </header>

        {sourceError && <div className="source-error">{sourceError}</div>}
        <section className="dashboard">
          <div className="page-heading">
            <div>
              <p className="eyebrow">PRODUCT INTELLIGENCE</p>
              <h1>{activePage}</h1>
              <p className="subtitle">
                Understand your product. Discover opportunities. Make better decisions.
              </p>
            </div>
            {activePage === "Overview" && (
              <div className="date-button">
                {analytics
                  ? `${analytics.period.start_date} – ${analytics.period.end_date}`
                  : "Latest available data"}
              </div>
            )}
          </div>

          {activePage === "Overview" ? (
            <>
              <div className="section-heading">
                <h2>Performance overview</h2>
                <span className="data-label">
                  {analyticsLoading
                    ? "Loading analytics…"
                    : hasAnalytics
                      ? "Live from uploaded dataset"
                      : "No event dataset connected"}
                </span>
              </div>

              {analyticsLoading && !hasAnalytics ? (
                <div className="panel loading-panel">
                  Loading your product metrics…
                </div>
              ) : analyticsError && !hasAnalytics ? (
                <div className="panel no-data-panel">
                  <BarChart3 size={30} />
                  <h3>No product analytics available</h3>
                  <p>{analyticsError}</p>
                  <button
                    className="primary-button"
                    onClick={() => setActivePage("Upload Data")}
                  >
                    <UploadCloud size={16} />
                    Upload event data
                  </button>
                </div>
              ) : hasAnalytics ? (
                <>
                  <div className="metrics-grid">
                    {metrics.map((metric) => {
                      const Icon = metric.icon;
                      return (
                        <div className="metric-card" key={metric.title}>
                          <div className="metric-top">
                            <span>{metric.title}</span>
                            <Icon size={19} />
                          </div>
                          <h2>{metric.value}</h2>
                          <p>{metric.description}</p>
                        </div>
                      );
                    })}
                  </div>

                  <div className="analytics-meta">
                    <span>
                      {numberFormatter.format(analytics.metrics.total_users)} total users
                    </span>
                    <span>
                      {numberFormatter.format(analytics.metrics.total_events)} events analysed
                    </span>
                    <span>Source: uploaded behavioural CSV</span>
                  </div>

                  <div className="content-grid">
                    <div className="panel chart-panel">
                      <div className="panel-heading">
                        <div>
                          <h3>User activity</h3>
                          <p>Daily unique active users in the available data window</p>
                        </div>
                        <span className="chart-tag">DAU</span>
                      </div>

                      {analytics.daily_activity.length > 0 ? (
                        <div className="analytics-chart">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart
                              data={analytics.daily_activity}
                              margin={{ top: 12, right: 8, left: -18, bottom: 0 }}
                            >
                              <defs>
                                <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="0%" stopColor="#786be9" stopOpacity={0.25} />
                                  <stop offset="95%" stopColor="#786be9" stopOpacity={0.02} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf0f5" />
                              <XAxis
                                dataKey="date"
                                tickFormatter={(value: string) => value.slice(5)}
                                tick={{ fill: "#8791a4", fontSize: 10 }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <YAxis
                                allowDecimals={false}
                                tick={{ fill: "#8791a4", fontSize: 10 }}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip
                                labelFormatter={(value) => `Date: ${value}`}
                                formatter={(value) => [value, "Active users"]}
                              />
                              <Area
                                type="monotone"
                                dataKey="active_users"
                                stroke="#786be9"
                                strokeWidth={2.5}
                                fill="url(#activityFill)"
                                activeDot={{ r: 5 }}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <div className="chart-empty">No daily activity records in this dataset.</div>
                      )}
                    </div>

                    <div className="panel">
                      <div className="panel-heading">
                        <div>
                          <h3>Conversion funnel</h3>
                          <p>Unique users reaching each event stage</p>
                        </div>
                        <TrendingUp size={19} />
                      </div>
                      <div className="funnel-chart">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={analytics.funnel}
                            layout="vertical"
                            margin={{ top: 8, right: 12, left: 8, bottom: 0 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#edf0f5" />
                            <XAxis type="number" allowDecimals={false} hide />
                            <YAxis
                              type="category"
                              dataKey="stage"
                              width={92}
                              tick={{ fill: "#697386", fontSize: 10 }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Tooltip formatter={(value) => [value, "Users"]} />
                            <Bar
                              dataKey="users"
                              fill="#786be9"
                              radius={[0, 5, 5, 0]}
                              barSize={22}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  <div className="panel bottom-panel">
                    <div className="panel-heading">
                      <div>
                        <h3>What these metrics mean</h3>
                        <p>Definitions used by the current PulseOS analytics service</p>
                      </div>
                      <Sparkles size={21} />
                    </div>
                    <div className="metric-definitions">
                      <p><strong>DAU:</strong> Unique users with at least one event on the latest date in the dataset.</p>
                      <p><strong>MAU:</strong> Unique users with at least one event in the 30-day window ending on that date.</p>
                      <p><strong>Conversion:</strong> Unique users with a purchase event divided by unique users with a product-view event. This is a user-level ratio, not a session-level funnel.</p>
                    </div>
                  </div>
                </>
              ) : null}
            </>
          ) : activePage === "Upload Data" ? (
            <UploadData />
          ) : activePage === "Product Analytics" ? (
            <ProductAnalytics key={dataContextKey} />
          ) : activePage === "Opportunities" ? (
            <ProductOpportunities key={dataContextKey} />
          ) : activePage === "Voice of Customer" ? (
            <VoiceOfCustomer key={dataContextKey} />
          ) : activePage === "AI Analyst" ? (
            <AIAnalyst key={dataContextKey} />
          ) : activePage === "Experiments" ? (
            <ExperimentIntelligence key={dataContextKey} />
          ) : activePage === "Strategy & Insights" ? (
            <ProductStrategy key={dataContextKey} />
          ) : activePage === "Health Scorecard" ? (
            <ProductHealthScorecard key={dataContextKey} />
          ) : activePage === "Cohort & Segments" ? (
            <CohortSegmentIntelligence key={dataContextKey} />
          ) : activePage === "Funnel & Journeys" ? (
            <FunnelJourneyIntelligence key={dataContextKey} />
          ) : activePage === "Root Cause Explorer" ? (
            <RootCauseExplorer key={dataContextKey} />
          ) : activePage === "Anomaly Detection" ? (
            <ProductAnomalies key={dataContextKey} />
          ) : activePage === "Churn Prediction" ? (
            <CustomerChurn key={dataContextKey} />
          ) : (
            <div className="panel page-placeholder">
              <Sparkles size={32} />
              <h3>{activePage}</h3>
              <p>
                This module will be implemented in an upcoming milestone.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
