import { useEffect, useState } from "react";
import { AlertCircle, ArrowRight, CheckCircle2, FlaskConical, MessageSquareText, RefreshCw, Search, TrendingDown, Users } from "lucide-react";
import { getRootCauseDiagnostics, type RootCauseDiagnosticsResponse, type RootCauseHypothesis } from "./services/api";
import "./RootCauseExplorer.css";

function signalIcon(type: string) {
  if (type === "Customer feedback") return MessageSquareText;
  if (type === "Segment disparity") return Users;
  return TrendingDown;
}

function HypothesisCard({ item, index }: { item: RootCauseHypothesis; index: number }) {
  const Icon = signalIcon(item.signal_type);
  return (
    <article className="panel root-cause-card">
      <div className="root-cause-card-top">
        <span className="root-cause-rank">#{index + 1}</span>
        <span className="root-cause-type"><Icon size={14} />{item.signal_type}</span>
        <span className={`root-cause-severity ${item.severity.toLowerCase()}`}>{item.severity}</span>
        <strong className="root-cause-score">{item.priority_score.toFixed(0)}<small>/100</small></strong>
      </div>
      <h3>{item.title}</h3>
      <p className="root-cause-observation">{item.observation}</p>
      <div className="root-cause-evidence">
        {item.evidence.map((evidence) => (
          <div key={evidence.label}><span>{evidence.label}</span><strong>{evidence.value ?? "—"}{evidence.unit ? ` ${evidence.unit}` : ""}</strong></div>
        ))}
      </div>
      {item.customer_context && item.customer_context.length > 0 && (
        <div className="root-cause-quotes">
          <strong>Customer evidence</strong>
          {item.customer_context.map((quote, quoteIndex) => (
            <blockquote key={quoteIndex}>“{quote.review_text}” <small>· {quote.rating}/5</small></blockquote>
          ))}
        </div>
      )}
      {item.segment_context && item.segment_context.length > 0 && (
        <div className="root-cause-segment-list">
          <strong>Segment comparison</strong>
          {item.segment_context.map((segment) => (
            <span key={segment.segment}>{segment.segment}: {segment.entry_to_completion_rate.toFixed(1)}% ({segment.units} units)</span>
          ))}
        </div>
      )}
      {item.experiment_context.length > 0 && (
        <div className="root-cause-experiment"><FlaskConical size={14} /> Existing experiment: {item.experiment_context.map((experiment) => experiment.name).join(", ")}</div>
      )}
      <div className="root-cause-next">
        <strong>What to investigate next</strong>
        <ul>{item.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>
      </div>
      <p className="root-cause-caveat"><AlertCircle size={14} />{item.caveat}</p>
    </article>
  );
}

function RootCauseExplorer() {
  const [data, setData] = useState<RootCauseDiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getRootCauseDiagnostics());
    } catch {
      setError("Unable to load diagnostic insights. Check that the backend is running and try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  return (
    <div className="root-cause-page">
      <div className="root-cause-toolbar">
        <p>Turn product signals into testable explanations—not assumptions.</p>
        <button onClick={() => void load()} disabled={loading}><RefreshCw size={14} /> Refresh diagnostics</button>
      </div>
      <section className="root-cause-hero">
        <span className="upload-eyebrow">PRODUCT DIAGNOSTICS</span>
        <h2>What might be driving product friction?</h2>
        <p>PulseOS combines funnel progression, customer feedback and segment differences to surface where investigation may have the highest value.</p>
        <div className="root-cause-source-tags">
          <span><CheckCircle2 size={13} /> Behavioural events</span>
          <span><CheckCircle2 size={13} /> Customer reviews</span>
          <span><FlaskConical size={13} /> Experiment register</span>
        </div>
      </section>

      {loading && !data && <div className="panel loading-panel">Building evidence-backed diagnostic hypotheses…</div>}
      {error && <div className="panel root-cause-error">{error}<button onClick={() => void load()}>Try again</button></div>}

      {data && (
        <>
          <section className="root-cause-metrics">
            <article className="panel"><Search size={17} /><span>Hypotheses</span><strong>{data.summary.hypotheses}</strong><small>Signals to validate</small></article>
            <article className="panel"><AlertCircle size={17} /><span>High priority</span><strong>{data.summary.high_priority}</strong><small>Based on observed signal strength</small></article>
            <article className="panel"><TrendingDown size={17} /><span>Funnel signals</span><strong>{data.summary.funnel_signals}</strong><small>Transitions with drop-off</small></article>
            <article className="panel"><MessageSquareText size={17} /><span>Customer signals</span><strong>{data.summary.customer_signals}</strong><small>Review-theme opportunities</small></article>
          </section>

          {data.status === "no_data" || data.status === "no_signals" ? (
            <div className="panel root-cause-empty">
              <Search size={25} />
              <h3>{data.status === "no_data" ? "Upload data to start diagnosing" : "No investigation signals found"}</h3>
              <p>{data.status === "no_data" ? "Upload behavioural events and/or customer reviews to generate diagnostic hypotheses." : "The current data did not surface measurable funnel drop-offs, customer opportunities or segment disparities."}</p>
            </div>
          ) : (
            <div className="root-cause-list">
              <div className="root-cause-list-heading"><div><h3>Ranked investigation hypotheses</h3><p>Higher scores indicate stronger observed signals, not higher causal certainty.</p></div><span>{data.hypotheses.length} signals</span></div>
              {data.hypotheses.map((item, index) => <HypothesisCard key={item.id} item={item} index={index} />)}
            </div>
          )}

          {data.data_gaps.length > 0 && (
            <section className="panel root-cause-gaps">
              <h3>Data coverage notes</h3>
              {data.data_gaps.map((gap) => <p key={gap}><ArrowRight size={13} />{gap}</p>)}
            </section>
          )}
          <section className="panel root-cause-method">
            <h3>How to interpret these diagnostics</h3>
            <p>{data.methodology}</p>
          </section>
        </>
      )}
    </div>
  );
}

export default RootCauseExplorer;
