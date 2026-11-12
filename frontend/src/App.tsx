import { useEffect, useState } from "react";

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
import "./App.css";

const navigation = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Upload Data", icon: UploadCloud },
  { name: "Product Analytics", icon: BarChart3 },
  { name: "Opportunities", icon: Target },
  { name: "Voice of Customer", icon: MessageSquareText },
  { name: "AI Analyst", icon: Sparkles },
  { name: "Experiments", icon: FlaskConical },
  { name: "Strategy & Insights", icon: Lightbulb },
  { name: "Health Scorecard", icon: Gauge },
  { name: "Cohort & Segments", icon: Users },
];

const numberFormatter = new Intl.NumberFormat("en-IN");
const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function App() {
  const [status, setStatus] = useState("Connecting...");
  const [activePage, setActivePage] = useState("Overview");
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Offline"));
  }, []);

  // Refresh when the user returns to Overview after uploading a dataset.
  useEffect(() => {
    if (activePage !== "Overview") return;

    let cancelled = false;
    setAnalyticsLoading(true);
    setAnalyticsError("");

    getAnalytics()
      .then((data) => {
        if (!cancelled) setAnalytics(data);
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
            : "Unable to load product analytics. Check that the backend is running.";

        setAnalyticsError(message);
      })
      .finally(() => {
        if (!cancelled) setAnalyticsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activePage]);

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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">P</div>
          <span>
            Pulse<span className="brand-light">OS</span>
          </span>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <nav>
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.name}
                className={`nav-item ${activePage === item.name ? "active" : ""}`}
                onClick={() => setActivePage(item.name)}
              >
                <Icon size={18} />
                <span>{item.name}</span>
              </button>
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
            <button className="icon-button" aria-label="Search">
              <Search size={19} />
            </button>
            <button className="icon-button" aria-label="Notifications">
              <Bell size={19} />
            </button>
            <div className="avatar small-avatar">DT</div>
          </div>
        </header>

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
            <ProductAnalytics />
          ) : activePage === "Opportunities" ? (
            <ProductOpportunities />
          ) : activePage === "Voice of Customer" ? (
            <VoiceOfCustomer />
          ) : activePage === "AI Analyst" ? (
            <AIAnalyst />
          ) : activePage === "Experiments" ? (
            <ExperimentIntelligence />
          ) : activePage === "Strategy & Insights" ? (
            <ProductStrategy />
          ) : activePage === "Health Scorecard" ? (
            <ProductHealthScorecard />
          ) : activePage === "Cohort & Segments" ? (
            <CohortSegmentIntelligence />
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
