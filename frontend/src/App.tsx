
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
  ArrowUpRight,
} from "lucide-react";

import { getHealth } from "./services/api";
import UploadData from "./UploadData";
import "./App.css";

const navigation = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Upload Data", icon: UploadCloud },
  { name: "Product Analytics", icon: BarChart3 },
  { name: "Voice of Customer", icon: MessageSquareText },
  { name: "AI Analyst", icon: Sparkles },
  { name: "Experiments", icon: FlaskConical },
];

const metrics = [
  {
    title: "Daily Active Users",
    value: "—",
    change: "Awaiting data",
    icon: Users,
  },
  {
    title: "Conversion Rate",
    value: "—",
    change: "Awaiting data",
    icon: TrendingUp,
  },
  {
    title: "Retention Rate",
    value: "—",
    change: "Awaiting data",
    icon: Activity,
  },
  {
    title: "Total Revenue",
    value: "—",
    change: "Awaiting data",
    icon: ArrowUpRight,
  },
];

function App() {
  const [status, setStatus] = useState("Connecting...");
  const [activePage, setActivePage] = useState("Overview");

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Offline"));
  }, []);

  return (
    <div className="app-shell">

      {/* Sidebar */}
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
                className={`nav-item ${
                  activePage === item.name ? "active" : ""
                }`}
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
              className={`status-dot ${
                status === "healthy" ? "" : "offline"
              }`}
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

      {/* Main content */}
      <main className="main-content">

        {/* Top navigation */}
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

        {/* Dashboard content */}
        <section className="dashboard">

          <div className="page-heading">

            <div>
              <p className="eyebrow">PRODUCT INTELLIGENCE</p>

              <h1>{activePage}</h1>

              <p className="subtitle">
                Understand your product. Discover opportunities.
                Make better decisions.
              </p>
            </div>

            <button className="date-button">
              Last 30 days ▾
            </button>

          </div>

          {/* Overview page */}
          {activePage === "Overview" ? (

            <>
              <div className="section-heading">
                <h2>Performance overview</h2>
                <span className="data-label">
                  No dataset connected
                </span>
              </div>

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

                      <p>{metric.change}</p>

                    </div>
                  );
                })}

              </div>

              <div className="content-grid">

                <div className="panel chart-panel">

                  <div className="panel-heading">
                    <div>
                      <h3>User activity</h3>
                      <p>Daily active users over time</p>
                    </div>

                    <span className="chart-tag">DAU</span>
                  </div>

                  <div className="empty-state">
                    <BarChart3 size={34} />

                    <strong>Waiting for event data</strong>

                    <span>
                      Upload a behavioural dataset to see user activity.
                    </span>
                  </div>

                </div>

                <div className="panel">

                  <div className="panel-heading">
                    <div>
                      <h3>Customer insights</h3>
                      <p>Voice of Customer overview</p>
                    </div>

                    <MessageSquareText size={19} />
                  </div>

                  <div className="empty-state">
                    <MessageSquareText size={34} />

                    <strong>No reviews analysed yet</strong>

                    <span>
                      Customer sentiment and recurring topics
                      will appear here.
                    </span>
                  </div>

                </div>

              </div>

              <div className="panel bottom-panel">

                <div className="panel-heading">
                  <div>
                    <h3>Get started with PulseOS</h3>
                    <p>
                      Your product intelligence workspace is ready.
                    </p>
                  </div>

                  <Sparkles size={21} />
                </div>

                <div className="getting-started">

                  <div>
                    <span>01</span>
                    Connect behavioural event data
                  </div>

                  <div>
                    <span>02</span>
                    Analyse customer reviews
                  </div>

                  <div>
                    <span>03</span>
                    Discover actionable insights
                  </div>

                </div>

              </div>
            </>

          ) : activePage === "Upload Data" ? (

            /* Upload Data page */
            <UploadData />

          ) : (

            /* Other modules - coming soon */
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
