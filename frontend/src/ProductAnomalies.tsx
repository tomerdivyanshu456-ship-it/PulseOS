import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { getProductAnomalies, type ProductAnomaliesResponse } from "./services/api";
import "./ProductAnomalies.css";

function ProductAnomalies() {
  const [data, setData] = useState<ProductAnomaliesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getProductAnomalies());
    } catch (err: unknown) {
      const detail = typeof err === "object" && err !== null && "response" in err &&
        typeof err.response === "object" && err.response !== null && "data" in err.response &&
        typeof err.response.data === "object" && err.response.data !== null && "detail" in err.response.data
        ? String(err.response.data.detail) : "Unable to analyse event data. Check that an event dataset is uploaded.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  if (loading) return <div className="panel anomaly-state">Analysing daily product activity…</div>;
  if (error || !data) return <div className="panel anomaly-state anomaly-error">{error || "No anomaly results."}<button onClick={() => void load()}>Try again</button></div>;

  return (
    <div className="anomaly-page">
      <div className="anomaly-toolbar">
        <p>UNSUPERVISED ML · {data.period.start_date} to {data.period.end_date} · {data.days_analyzed} days</p>
        <button onClick={() => void load()}><RefreshCw size={14}/> Refresh analysis</button>
      </div>
      <section className="anomaly-intro">
        <span className="upload-eyebrow">ISOLATION FOREST</span>
        <h2>Find unusual shifts in product activity.</h2>
        <p>Daily event volume, active users, purchases and revenue are evaluated independently against the uploaded history.</p>
      </section>
      <section className="anomaly-summary-grid">
        <article className="panel"><span>Flagged observations</span><strong>{data.anomaly_count}</strong><small>Across {data.metrics_analyzed.length} varying metrics</small></article>
        <article className="panel"><span>Observation window</span><strong>{data.days_analyzed} days</strong><small>Up to the latest 90 available dates</small></article>
      </section>
      <section className="panel anomaly-section">
        <div className="anomaly-section-heading"><div><h3>Detected anomalies</h3><p>Sorted by model anomaly score. Higher scores indicate more unusual observations.</p></div><AlertTriangle size={19}/></div>
        {data.anomalies.length ? <div className="anomaly-table-wrap"><table className="anomaly-table"><thead><tr><th>Date</th><th>Metric</th><th>Observed</th><th>Median</th><th>Signal</th><th>Score</th></tr></thead><tbody>
          {data.anomalies.map((item) => <tr key={item.date + item.metric}><td>{item.date}</td><td>{item.label}</td><td>{item.value.toLocaleString("en-IN")}</td><td>{item.baseline_median.toLocaleString("en-IN")}</td><td><span className={item.direction === "spike" ? "anomaly-signal spike" : "anomaly-signal drop"}>{item.direction === "spike" ? <TrendingUp size={12}/> : <TrendingDown size={12}/>} {item.direction}</span></td><td>{item.anomaly_score.toFixed(3)}</td></tr>)}
        </tbody></table></div> : <div className="analytics-insufficient-data"><strong>No unusual observations were flagged.</strong><p>This does not guarantee that product activity is free of issues.</p></div>}
        {data.data_gaps.map((gap) => <p className="anomaly-note" key={gap}>{gap}</p>)}
      </section>
      <section className="panel anomaly-section"><h3>Methodology & limitations</h3><p>{data.methodology}</p><ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </div>
  );
}

export default ProductAnomalies;
