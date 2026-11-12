import { useEffect, useState } from "react";
import { RefreshCw, Users, Layers3, Activity, ShoppingCart } from "lucide-react";
import { getSegmentIntelligence, type SegmentIntelligenceResponse } from "./services/api";
import "./CohortSegmentIntelligence.css";

function CohortSegmentIntelligence() {
  const [data, setData] = useState<SegmentIntelligenceResponse | null>(null);
  const [dimension, setDimension] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(selected?: string) {
    setLoading(true);
    setError("");
    try {
      const result = await getSegmentIntelligence(selected || undefined);
      setData(result);
      setDimension(result.selected_dimension || "");
    } catch {
      setError("Unable to load segment intelligence. Check the backend and confirm that an event dataset has been uploaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);
  const segments = data?.segments || [];
  const bestRepeat = [...segments].sort((a, b) => b.repeat_user_rate - a.repeat_user_rate)[0];
  const bestPurchase = [...segments].sort((a, b) => b.purchase_user_rate - a.purchase_user_rate)[0];
  const hasRevenue = segments.some((item) => item.revenue_per_user !== undefined);

  return (
    <div className="segment-page">
      <div className="segment-toolbar">
        <p>Compare user behaviour across attributes present in your event data.</p>
        <button onClick={() => void load(dimension)} disabled={loading}><RefreshCw size={14} /> Refresh</button>
      </div>
      {loading ? <div className="panel loading-panel">Analysing user segments…</div> : error ? (
        <div className="panel segment-empty">{error}<button onClick={() => void load(dimension)}>Try again</button></div>
      ) : data?.status === "no_dimensions" ? (
        <div className="panel segment-empty"><Layers3 size={22} /><strong>No segment attributes detected</strong><p>{data.methodology}</p><p>Upload event data with categorical fields such as platform, plan, region, or acquisition_channel.</p></div>
      ) : data ? (
        <>
          <section className="segment-intro">
            <span className="upload-eyebrow">COHORT & SEGMENT INTELLIGENCE</span>
            <h2>Discover which user groups engage, return and convert.</h2>
            <p>Choose an available event attribute to compare user-level behaviour across its values.</p>
            <label>Segment by
              <select value={dimension} onChange={(event) => void load(event.target.value)}>
                {data.dimensions.map((item) => <option value={item.key} key={item.key}>{item.label} · {item.values} values</option>)}
              </select>
            </label>
            <small>Observed period: {data.period?.start_date} to {data.period?.end_date}</small>
          </section>
          <section className="segment-summary-grid">
            <article className="panel segment-summary-card"><Users size={17} /><span>Users assigned</span><strong>{data.assigned_users.toLocaleString()}</strong><small>{data.unassigned_users.toLocaleString()} users lack this attribute</small></article>
            <article className="panel segment-summary-card"><Layers3 size={17} /><span>Segments found</span><strong>{segments.length}</strong></article>
            <article className="panel segment-summary-card"><Activity size={17} /><span>Highest repeat rate</span><strong>{bestRepeat ? `${bestRepeat.repeat_user_rate}%` : "—"}</strong><small>{bestRepeat?.segment || "No segment data"}</small></article>
            <article className="panel segment-summary-card"><ShoppingCart size={17} /><span>Highest purchase-user rate</span><strong>{bestPurchase ? `${bestPurchase.purchase_user_rate}%` : "—"}</strong><small>{bestPurchase?.segment || "No segment data"}</small></article>
          </section>
          <section className="panel product-analytics-section">
            <div className="product-analytics-section-heading"><div><h3>Segment comparison</h3><p>Each user is assigned to one value of the selected attribute.</p></div><Users size={19} /></div>
            <div className="retention-table-wrap">
              <table className="segment-table">
                <thead><tr><th>Segment</th><th>Users</th><th>User share</th><th>Events / user</th><th>Repeat user rate</th><th>Purchase user rate</th>{hasRevenue && <th>Revenue / user</th>}</tr></thead>
                <tbody>{segments.map((item) => <tr key={item.segment}><td><strong>{item.segment}</strong></td><td>{item.users.toLocaleString()}</td><td>{item.user_share.toFixed(1)}%</td><td>{item.events_per_user.toFixed(2)}</td><td>{item.repeat_user_rate.toFixed(1)}%</td><td>{item.purchase_user_rate.toFixed(1)}%</td>{hasRevenue && <td>{item.revenue_per_user === undefined ? "—" : item.revenue_per_user.toFixed(2)}</td>}</tr>)}</tbody>
              </table>
            </div>
            <p className="product-analytics-footnote">{data.methodology}</p>
          </section>
        </>
      ) : null}
    </div>
  );
}

export default CohortSegmentIntelligence;