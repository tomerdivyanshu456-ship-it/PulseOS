import { useEffect, useState } from "react";
import { Activity, CalendarDays, Layers3, RefreshCw, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAnalytics, type AnalyticsOverview } from "./services/api";
import "./ProductAnalytics.css";

function ProductAnalytics() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getAnalytics());
    } catch {
      setError("Unable to load product analytics. Check the backend and confirm that an event dataset has been uploaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <div className="panel loading-panel">Calculating retention and adoption metrics…</div>;
  if (error || !data) return <div className="panel product-analytics-error">{error || "No analytics available."}<button onClick={() => void load()}>Try again</button></div>;

  const hasRepeatWeeks = data.retention_cohorts.some((cohort) => cohort.weeks.length > 1);

  return (
    <div className="product-analytics-page">
      <div className="product-analytics-toolbar">
        <p>Behavioural analysis · {data.period.start_date} to {data.period.end_date}</p>
        <button onClick={() => void load()}><RefreshCw size={14} /> Refresh analysis</button>
      </div>

      <section className="product-analytics-intro">
        <div>
          <span className="upload-eyebrow">PRODUCT USAGE</span>
          <h2>Understand engagement beyond the headline metrics.</h2>
          <p>Explore when users return and which tracked events reach the most users.</p>
        </div>
      </section>

      <section className="product-analytics-grid">
        <article className="panel product-analytics-card">
          <div><Users size={17} /><span>Unique users</span></div>
          <strong>{data.metrics.total_users}</strong>
          <small>Across the uploaded event dataset</small>
        </article>
        <article className="panel product-analytics-card">
          <div><Activity size={17} /><span>Repeat users</span></div>
          <strong>{data.metrics.repeat_users}</strong>
          <small>{data.metrics.repeat_user_rate}% active on 2+ distinct days</small>
        </article>
        <article className="panel product-analytics-card">
          <div><CalendarDays size={17} /><span>Repeat user rate</span></div>
          <strong>{data.metrics.repeat_user_rate}%</strong>
          <small>Users active on multiple calendar days</small>
        </article>
        <article className="panel product-analytics-card">
          <div><Layers3 size={17} /><span>Tracked event types</span></div>
          <strong>{data.event_adoption.length}</strong>
          <small>Distinct event names in the dataset</small>
        </article>
        <article className="panel product-analytics-card">
          <div><Activity size={17} /><span>Events per user</span></div>
          <strong>{data.metrics.average_events_per_user}</strong>
          <small>Average events per unique user</small>
        </article>
      </section>

      <section className="panel product-analytics-section">
        <div className="product-analytics-section-heading">
          <div><h3>Weekly retention cohorts</h3><p>Each row groups users by the week they first appeared. Cells show the percentage active in each subsequent week.</p></div>
          <Layers3 size={19} />
        </div>
        {hasRepeatWeeks ? (
          <div className="retention-table-wrap">
            <table className="retention-table">
              <thead><tr><th>First active week</th><th>Users</th><th>Week 0</th><th>Week 1</th><th>Week 2</th><th>Week 3</th></tr></thead>
              <tbody>
                {data.retention_cohorts.map((cohort) => (
                  <tr key={cohort.cohort}>
                    <td>{cohort.cohort}</td>
                    <td>{cohort.cohort_size}</td>
                    {[0, 1, 2, 3].map((week) => {
                      const cell = cohort.weeks.find((item) => item.week === week);
                      return <td key={week}>{cell ? <span className="retention-cell">{cell.retention_rate.toFixed(1)}%</span> : <span className="retention-unavailable">—</span>}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="analytics-insufficient-data">
            <strong>Not enough history to calculate repeat-week retention yet.</strong>
            <p>The uploaded data currently covers too little time to observe users returning in a later week. Week 0 is not evidence of retention. Upload event data spanning multiple weeks to populate the cohort table.</p>
          </div>
        )}
        <p className="product-analytics-footnote">Cohorts are based on the first observed event week in this dataset. Later weeks are only shown when the dataset contains enough elapsed time.</p>
      </section>

      <section className="panel product-analytics-section">
        <div className="product-analytics-section-heading">
          <div><h3>Event adoption</h3><p>Share of unique users who triggered each event at least once.</p></div>
          <Activity size={19} />
        </div>
        {data.event_adoption.length > 0 ? (
          <div className="event-adoption-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.event_adoption} layout="vertical" margin={{ top: 4, right: 24, left: 12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#edf0f5" />
                <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fill: "#8791a4", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="event_name" width={125} tick={{ fill: "#697386", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value) => [`${value}%`, "User adoption"]} />
                <Bar dataKey="user_adoption_rate" fill="#786be9" radius={[0, 5, 5, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <p className="analytics-insufficient-data">No event types are available.</p>}
        <div className="event-adoption-list">
          {data.event_adoption.map((event) => (
            <div key={event.event_name}>
              <strong>{event.event_name}</strong>
              <span>{event.active_users} users · {event.event_count} events · {event.user_adoption_rate}% adoption</span>
            </div>
          ))}
        </div>
        <p className="product-analytics-footnote">{data.adoption_note}</p>
      </section>
    </div>
  );
}

export default ProductAnalytics;
