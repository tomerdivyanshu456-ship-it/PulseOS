import { useEffect, useState } from "react";
import { AlertTriangle, ArrowDownUp, CheckCircle2, CircleHelp, Compass, RefreshCw, Sparkles, Target } from "lucide-react";
import {
  getProductStrategy,
  prioritiseProductStrategy,
  type ProductStrategyResponse,
} from "./services/api";
import "./ProductStrategy.css";

function ProductStrategy() {
  const [data, setData] = useState<ProductStrategyResponse | null>(null);
  const [effortEstimates, setEffortEstimates] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [savingEffort, setSavingEffort] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getProductStrategy());
    } catch {
      setError("Unable to generate product strategy. Check that the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function updateEffort(id: string, effort: number) {
    const next = { ...effortEstimates, [id]: effort };
    setEffortEstimates(next);
    setSavingEffort(true);
    setError("");
    try {
      setData(await prioritiseProductStrategy(next));
    } catch {
      setError("Could not recalculate priorities. Your previous ranking is still shown.");
    } finally {
      setSavingEffort(false);
    }
  }

  if (loading) return <div className="panel loading-panel">Synthesising customer, behavioural and experiment evidence…</div>;
  if (error && !data) return <div className="panel strategy-error">{error}<button onClick={() => void load()}>Try again</button></div>;
  if (!data) return null;

  return (
    <div className="strategy-page">
      <div className="strategy-toolbar">
        <p>Evidence-led roadmap · Customer signals + product behaviour + experiments</p>
        <button onClick={() => void load()} disabled={savingEffort}><RefreshCw size={14} /> Refresh strategy</button>
      </div>

      <section className="strategy-intro">
        <span className="upload-eyebrow">PRODUCT STRATEGY WORKSPACE</span>
        <h2>Turn product evidence into your next best actions.</h2>
        <p>PulseOS ranks investigation opportunities, explains the evidence behind each one and suggests how to measure progress. Adjust effort to see how the roadmap changes.</p>
      </section>

      <div className="strategy-source-status">
        <span className={data.sources.events ? "source-ready" : "source-missing"}>{data.sources.events ? "✓" : "!"} Behavioural events</span>
        <span className={data.sources.reviews ? "source-ready" : "source-missing"}>{data.sources.reviews ? "✓" : "!"} Customer reviews</span>
        <span className="source-status-label">{data.status === "ready" ? "Full evidence set" : data.status === "partial" ? "Partial evidence set" : "Awaiting data"}</span>
      </div>

      {error && <div className="strategy-inline-error"><AlertTriangle size={15} />{error}</div>}
      {data.data_gaps.length > 0 && (
        <div className="strategy-data-gap"><AlertTriangle size={16} /><div><strong>Evidence gaps</strong><p>{data.data_gaps.join(" · ")}</p></div></div>
      )}

      <div className="strategy-summary-grid">
        <article className="strategy-summary-card"><span>Opportunities reviewed</span><strong>{data.summary.opportunities_reviewed}</strong><small>From uploaded evidence</small></article>
        <article className="strategy-summary-card"><span>High-priority candidates</span><strong>{data.summary.high_priority_count}</strong><small>Priority score ≥ 50</small></article>
        <article className="strategy-summary-card"><span>Opportunities with experiments</span><strong>{data.summary.experiments_linked}</strong><small>Existing linked experiments</small></article>
      </div>

      <div className="strategy-section-heading">
        <div><span className="upload-eyebrow">RECOMMENDED ROADMAP</span><h3>What should the team investigate next?</h3></div>
        <span className="strategy-sort-label"><ArrowDownUp size={14} /> Ranked by priority score</span>
      </div>

      {data.recommendations.length > 0 ? (
        <section className="strategy-recommendations">
          {data.recommendations.map((item) => (
            <article className="panel strategy-card" key={item.id}>
              <div className="strategy-card-top">
                <div className="strategy-rank">#{item.rank}</div>
                <div className="strategy-card-title"><span>{item.feature}</span><h3>{item.title}</h3></div>
                <div className="strategy-score"><strong>{item.priority_score.toFixed(1)}</strong><small>Priority score</small></div>
              </div>

              <div className="strategy-score-breakdown">
                <div><span>Impact</span><strong>{item.impact_score.toFixed(0)}/100</strong></div>
                <div><span>Evidence confidence</span><strong>{item.confidence_score.toFixed(0)}/100</strong></div>
                <label><span>Estimated effort</span>
                  <select value={effortEstimates[item.id] ?? item.effort_estimate} onChange={(event) => void updateEffort(item.id, Number(event.target.value))} disabled={savingEffort}>
                    <option value={1}>1 · Very low</option>
                    <option value={2}>2 · Low</option>
                    <option value={3}>3 · Medium</option>
                    <option value={4}>4 · High</option>
                    <option value={5}>5 · Very high</option>
                  </select>
                </label>
              </div>

              <div className="strategy-evidence-grid">
                <div><span>Customer evidence</span><strong>{item.customer_evidence.review_count} negative reviews</strong><small>{item.customer_evidence.average_rating == null ? "Average rating unavailable" : `Average rating ${item.customer_evidence.average_rating.toFixed(1)}/5`}</small></div>
                <div><span>Behavioural evidence</span><strong>{item.behavioral_evidence ? `${item.behavioral_evidence.value.toLocaleString()} ${item.behavioral_evidence.unit}` : "Not available"}</strong><small>{item.behavioral_evidence?.label ?? "No matching event signal"}</small></div>
                <div><span>Experiment coverage</span><strong>{item.linked_experiment_count > 0 ? `${item.linked_experiment_count} linked` : "No linked experiment"}</strong><small>{item.experiment_names.join(", ") || "Consider validating with an experiment"}</small></div>
              </div>

              <div className="strategy-action-block"><div><Compass size={16}/><strong>Recommended next action</strong></div><p>{item.action}</p></div>
              <div className="strategy-measure-block"><div><Target size={16}/><strong>Success measurement</strong></div><p><b>Metric:</b> {item.expected_metric}</p><p>{item.success_measurement}</p></div>

              {item.customer_evidence.examples.length > 0 && <div className="strategy-quotes"><strong>Customer voice</strong>{item.customer_evidence.examples.map((quote, index) => <blockquote key={index}>“{quote.review_text}” <span>{quote.rating}/5</span></blockquote>)}</div>}
              <p className="strategy-evidence-note"><CheckCircle2 size={13}/>{item.evidence_note}</p>
            </article>
          ))}
        </section>
      ) : (
        <div className="panel strategy-empty"><Sparkles size={24}/><strong>No strategy recommendations yet.</strong><p>Upload customer reviews and/or behavioural event data, then refresh. A missing match does not mean there are no product problems.</p></div>
      )}

      <section className="panel strategy-methodology">
        <div><CircleHelp size={18}/><h3>How the priority score works</h3></div>
        <p>{data.methodology}</p>
        <p><b>Formula:</b> Impact score × evidence confidence × (3 ÷ effort estimate). Change effort from 1 (very low) to 5 (very high) to recalculate the ranking.</p>
        <p>These scores are decision-support heuristics. They are not financial forecasts, statistical confidence intervals, or proof that a customer complaint caused a behavioural drop-off.</p>
      </section>
    </div>
  );
}

export default ProductStrategy;
