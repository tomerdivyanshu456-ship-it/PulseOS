import { useEffect, useState } from "react";
import { AlertTriangle, ArrowUpRight, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { getProductOpportunities, type ProductOpportunitiesResponse } from "./services/api";
import "./ProductOpportunities.css";

function ProductOpportunities() {
  const [data, setData] = useState<ProductOpportunitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getProductOpportunities());
    } catch {
      setError("Unable to identify product opportunities. Check that the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <div className="panel loading-panel">Connecting product behaviour with customer feedback…</div>;
  if (error || !data) return <div className="panel opportunity-error">{error || "No opportunity data available."}<button onClick={() => void load()}>Try again</button></div>;

  return (
    <div className="opportunities-page">
      <div className="opportunities-toolbar">
        <p>Cross-source analysis · Behavioural events + customer reviews</p>
        <button onClick={() => void load()}><RefreshCw size={14} /> Refresh analysis</button>
      </div>

      <section className="opportunities-intro">
        <span className="upload-eyebrow">PRODUCT DECISION SUPPORT</span>
        <h2>Find product problems worth investigating.</h2>
        <p>PulseOS connects behavioural signals with customer feedback to generate evidence-backed investigation opportunities.</p>
      </section>

      <div className="opportunity-source-status">
        <span className={data.sources?.events ? "source-ready" : "source-missing"}>{data.sources?.events ? "✓" : "!"} Behavioural events</span>
        <span className={data.sources?.reviews ? "source-ready" : "source-missing"}>{data.sources?.reviews ? "✓" : "!"} Customer reviews</span>
        <span className="source-status-label">{data.status === "ready" ? "Both sources connected" : data.status === "partial" ? "Partial analysis" : "No data connected"}</span>
      </div>

      {data.data_gaps.length > 0 && (
        <div className="opportunity-data-gap"><AlertTriangle size={16} /><div><strong>Some evidence is unavailable</strong><p>{data.data_gaps.join(" · ")}</p></div></div>
      )}

      {data.opportunities.length > 0 ? (
        <section className="opportunity-cards">
          {data.opportunities.map((item) => (
            <article className="panel opportunity-card" key={item.id}>
              <div className="opportunity-card-heading">
                <div><span className="opportunity-feature">{item.feature}</span><h3>{item.title}</h3></div>
                <span className={`opportunity-priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span>
              </div>
              <div className="opportunity-signal-grid">
                <div className="opportunity-signal">
                  <span>Customer signal</span>
                  <strong>{item.customer_signal.review_count} negative review{item.customer_signal.review_count === 1 ? "" : "s"}</strong>
                  <small>{item.customer_signal.topic} · Avg. rating {item.customer_signal.average_rating.toFixed(1)}/5</small>
                </div>
                <div className="opportunity-signal">
                  <span>Behavioural signal</span>
                  {item.behavior_signal ? <>
                    <strong>{item.behavior_signal.value} {item.behavior_signal.unit}</strong>
                    <small>{item.behavior_signal.label}</small>
                  </> : <><strong>Not available</strong><small>No matching event signal found</small></>}
                </div>
              </div>
              {item.customer_signal.evidence.length > 0 && (
                <div className="opportunity-quotes">
                  <strong>Customer evidence</strong>
                  {item.customer_signal.evidence.map((evidence, index) => (
                    <blockquote key={index}>“{evidence.review_text}” <span>{evidence.rating}/5</span></blockquote>
                  ))}
                </div>
              )}
              <div className="opportunity-recommendation">
                <div><Sparkles size={15} /><strong>Recommended investigation</strong></div>
                <p>{item.recommendation}</p>
              </div>
              <p className="opportunity-confidence"><ShieldCheck size={13} /> {item.confidence_note}</p>
            </article>
          ))}
        </section>
      ) : (
        <div className="panel opportunity-empty">
          <ArrowUpRight size={24} />
          <strong>No cross-source opportunities detected yet.</strong>
          <p>Upload behavioural events and customer reviews containing themes recognised by the current mapping. A missing match does not mean there are no product problems.</p>
        </div>
      )}

      <section className="panel opportunity-methodology">
        <h3>How PulseOS identifies opportunities</h3>
        <p>{data.methodology}</p>
      </section>
    </div>
  );
}

export default ProductOpportunities;
