import { useEffect, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, Gauge, Info, RefreshCw, ShieldAlert } from "lucide-react";
import { getProductHealthScorecard, type ProductHealthScorecardResponse } from "./services/api";
import "./ProductHealthScorecard.css";

function ProductHealthScorecard() {
  const [data, setData] = useState<ProductHealthScorecardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    getProductHealthScorecard()
      .then(setData)
      .catch(() => setError("Could not load the health scorecard. Check that the backend is running."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const statusLabel = (status: string) =>
    status === "healthy" ? "Healthy" : status === "needs_attention" ? "Needs attention" : "At risk";

  const StatusIcon = ({ status }: { status: string }) => {
    if (status === "healthy") return <CheckCircle2 size={16} />;
    if (status === "needs_attention") return <AlertTriangle size={16} />;
    return <ShieldAlert size={16} />;
  };

  if (loading && !data) return <div className="health-loading">Calculating product health from your uploaded data…</div>;
  if (error && !data) return <div className="panel health-empty"><AlertTriangle size={25} /><strong>Scorecard unavailable</strong><p>{error}</p><button onClick={load}>Try again</button></div>;
  if (!data) return null;

  return (
    <div className="health-page">
      <div className="health-toolbar">
        <div className="health-source-row">
          <span className={data.sources.events ? "connected" : "disconnected"}><i />Behavioural events</span>
          <span className={data.sources.reviews ? "connected" : "disconnected"}><i />Customer reviews</span>
          <span className={data.sources.experiments ? "connected" : "disconnected"}><i />Experiment links</span>
          {data.period && <small>{data.period.start_date} – {data.period.end_date}</small>}
        </div>
        <button onClick={load} disabled={loading}><RefreshCw size={14} />{loading ? "Refreshing…" : "Refresh scorecard"}</button>
      </div>

      {error && <div className="health-inline-error">{error}</div>}

      <section className="health-hero">
        <div className="health-hero-copy">
          <span className="health-eyebrow">PRODUCT HEALTH SNAPSHOT</span>
          <h2>One view of product performance.</h2>
          <p>Bring engagement, conversion, customer sentiment and experimentation coverage into one evidence-aware diagnostic.</p>
        </div>
        <div className="health-overall">
          <div className="health-gauge"><Gauge size={19} /><strong>{data.overall_score === null ? "—" : data.overall_score}</strong><small>/ 100</small></div>
          <span className={data.status === "ready" ? "health-ready" : data.status === "partial" ? "health-partial" : "health-missing"}>{data.overall_label}</span>
          <small>{data.score_coverage.available_pillars} of {data.score_coverage.total_pillars} pillars available</small>
        </div>
      </section>

      {data.data_gaps.length > 0 && (
        <div className="health-gaps"><Info size={17} /><div><strong>Some evidence is missing</strong>{data.data_gaps.map((gap) => <p key={gap}>{gap}</p>)}</div></div>
      )}

      {data.pillars.length > 0 ? (
        <>
          <div className="health-section-heading"><div><span className="health-eyebrow">HEALTH DIMENSIONS</span><h3>How the product is performing</h3></div><small>Scores are diagnostic, not industry rankings</small></div>
          <div className="health-pillar-grid">
            {data.pillars.map((pillar) => (
              <article className="health-pillar panel" key={pillar.id}>
                <div className="health-pillar-top">
                  <div><span className="health-pillar-kicker">{pillar.title}</span><h3>{pillar.score}<small>/100</small></h3></div>
                  <span className={`health-status ${pillar.status}`}><StatusIcon status={pillar.status} />{statusLabel(pillar.status)}</span>
                </div>
                <p className="health-pillar-summary">{pillar.summary}</p>
                <div className="health-score-track"><span style={{ width: `${pillar.score}%` }} /></div>
                <div className="health-metric-list">
                  {pillar.metrics.map((metric) => <div key={metric.label}><span>{metric.label}</span><strong>{metric.value.toLocaleString("en-IN")}{metric.unit === "%" ? "%" : metric.unit === "/ 5" ? " / 5" : ` ${metric.unit}`}</strong></div>)}
                </div>
                <div className="health-benchmark"><strong>Reference:</strong> {pillar.benchmark}</div>
                <p className="health-caveat">{pillar.caveat}</p>
                <small className="health-source">Source: {pillar.source}</small>
              </article>
            ))}
          </div>
        </>
      ) : (
        <div className="panel health-empty"><Activity size={28} /><strong>Upload data to calculate product health</strong><p>Add behavioural events and customer reviews. The scorecard will only calculate dimensions supported by available evidence.</p></div>
      )}

      <div className="health-insight-grid">
        <div className="panel health-insight">
          <div><CheckCircle2 size={17} /><strong>Strongest areas</strong></div>
          {data.strongest_areas.length ? data.strongest_areas.map((item) => <p key={item.title}><span>{item.title}</span><b>{item.score}/100</b></p>) : <small>No scored areas yet.</small>}
        </div>
        <div className="panel health-insight">
          <div><AlertTriangle size={17} /><strong>Areas to investigate</strong></div>
          {data.areas_to_investigate.length ? data.areas_to_investigate.map((item) => <p key={item.title}><span>{item.title}</span><b>{item.score}/100</b></p>) : <small>No scored areas yet.</small>}
        </div>
      </div>

      <section className="panel health-methodology">
        <div><Info size={17} /><h3>How to interpret this score</h3></div>
        <p>{data.methodology}</p>
        <p>Calibrate the starter thresholds to the product's business model and historical baseline before using this score in an operating review. A missing dimension is excluded from the average and shown in the coverage count; it is never silently treated as zero.</p>
      </section>
    </div>
  );
}

export default ProductHealthScorecard;
