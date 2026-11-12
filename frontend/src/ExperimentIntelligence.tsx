import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Beaker, CheckCircle2, FlaskConical, Play, RefreshCw, Save, Target } from "lucide-react";
import {
  analyzeExperiment, createExperiment, getExperiments, getProductOpportunities,
  generateExperimentPlan, updateExperimentStatus,
  type Experiment, type ExperimentAnalysis, type ExperimentDraft,
  type ProductOpportunitiesResponse, type ExperimentDecision,
  getExperimentDecision,
} from "./services/api";
import "./ExperimentIntelligence.css";

const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const initialDraft: ExperimentDraft = {
  name: "", opportunity_id: "", opportunity_title: "", hypothesis: "", rationale: "",
  primary_metric: "Purchase conversion rate",
  secondary_metrics: [
    { name: "Engagement rate", definition: "Eligible users completing a meaningful engagement event." },
    { name: "Repeat usage rate", definition: "Eligible users returning to use the feature again." },
  ],
  guardrails: [
    { name: "Crash/error rate", direction: "must not increase" },
    { name: "Refund/cancellation rate", direction: "must not increase" },
    { name: "Task latency", direction: "must not materially increase" },
  ],
  baseline_rate: 0.1, minimum_detectable_effect: 0.02,
  confidence_level: 0.95, power: 0.8, daily_eligible_users: 1000,
};

function ExperimentIntelligence() {
  const [opportunities, setOpportunities] = useState<ProductOpportunitiesResponse["opportunities"]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [draft, setDraft] = useState<ExperimentDraft>(initialDraft);
  const [selectedId, setSelectedId] = useState("");
  const [analysis, setAnalysis] = useState<ExperimentAnalysis | null>(null);
  const [eventDecision, setEventDecision] = useState<ExperimentDecision | null>(null);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionInputs, setDecisionInputs] = useState({
    exposure_event: "experiment_exposed",
    conversion_event: "purchase",
    guardrail_event: "",
    guardrail_max_increase: 0,
  });
  const [guardrailInputs, setGuardrailInputs] = useState<Record<string, { control: number; variant: number; maxIncrease: number }>>({});
  const [counts, setCounts] = useState({ control_users: 1000, control_conversions: 100, variant_users: 1000, variant_conversions: 110 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selected = useMemo(() => experiments.find((item) => item.id === selectedId) ?? null, [experiments, selectedId]);
  const estimate = useMemo(() => {
    const p = draft.baseline_rate, lift = draft.minimum_detectable_effect;
    if (!(p > 0 && p < 1 && lift > 0 && p + lift < 1)) return null;
    const za = draft.confidence_level === 0.99 ? 2.575829 : draft.confidence_level === 0.90 ? 1.644854 : 1.959964;
    const zp = draft.power === 0.90 ? 1.281552 : 0.841621;
    const q = p + lift, pooled = (p + q) / 2;
    const n = Math.ceil(Math.pow(za * Math.sqrt(2 * pooled * (1 - pooled)) + zp * Math.sqrt(p * (1 - p) + q * (1 - q)), 2) / (lift * lift));
    return { perArm: n, total: 2 * n, days: Math.ceil((2 * n) / Math.max(1, draft.daily_eligible_users)) };
  }, [draft.baseline_rate, draft.minimum_detectable_effect, draft.confidence_level, draft.power, draft.daily_eligible_users]);

  async function load() {
    setLoading(true); setError("");
    try {
      const [opData, expData] = await Promise.all([getProductOpportunities(), getExperiments()]);
      setOpportunities(opData.opportunities); setExperiments(expData);
      if (expData.length && !selectedId) setSelectedId(expData[0].id);
    } catch {
      setError("Could not load experiment workspace. Check that the PulseOS API is running.");
    } finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  async function chooseOpportunity(id: string) {
    const item = opportunities.find((op) => op.id === id);
    setDraft((current) => ({ ...current, opportunity_id: id, opportunity_title: item?.title ?? "" }));
    setAnalysis(null); setEventDecision(null);
    if (!item) return;
    try {
      const plan = await generateExperimentPlan(item);
      setDraft((current) => ({
        ...current, name: plan.name, opportunity_id: id, opportunity_title: item.title,
        hypothesis: plan.hypothesis, rationale: plan.rationale,
        primary_metric: plan.primary_metric.name,
        secondary_metrics: plan.secondary_metrics, guardrails: plan.guardrails,
      }));
      setNotice("Draft hypothesis generated. Review and edit it before saving.");
    } catch { setError("Could not generate a hypothesis for this opportunity."); }
  }

  function edit<K extends keyof ExperimentDraft>(key: K, value: ExperimentDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    setSaving(true); setError(""); setNotice("");
    try {
      const created = await createExperiment(draft);
      setExperiments((current) => [created, ...current]); setSelectedId(created.id);
      setGuardrailInputs({});
      setNotice("Experiment saved to your local PulseOS workspace.");
    } catch (err) { setError(errorMessage(err, "Could not save this experiment. Check the required fields.")); }
    finally { setSaving(false); }
  }

  async function setStatus(id: string, status: Experiment["status"]) {
    try {
      const updated = await updateExperimentStatus(id, status);
      setExperiments((current) => current.map((item) => item.id === id ? updated : item));
    } catch { setError("Could not update experiment status."); }
  }

  async function runAnalysis() {
    setError("");
    try {
      const result = await analyzeExperiment({
        ...counts,
        planned_sample_size_per_arm: selected?.sample_size_per_arm,
        confidence_level: selected?.confidence_level ?? 0.95,
        guardrails: selected?.guardrails.map((item) => ({
          name: item.name,
          control_rate: (guardrailInputs[item.name]?.control ?? 0) / 100,
          variant_rate: (guardrailInputs[item.name]?.variant ?? 0) / 100,
          max_increase: (guardrailInputs[item.name]?.maxIncrease ?? 0) / 100,
        })) ?? [],
      });
      setAnalysis(result);
    } catch (err) { setError(errorMessage(err, "Could not analyse the entered results.")); }
  }

  async function runEventDecision() {
    if (!selected) {
      setError("Select a saved experiment before generating a decision.");
      return;
    }
    setDecisionLoading(true); setError(""); setEventDecision(null);
    try {
      const guardrails = decisionInputs.guardrail_event.trim()
        ? [{
            name: "Configured guardrail",
            event_name: decisionInputs.guardrail_event.trim(),
            max_increase: decisionInputs.guardrail_max_increase / 100,
          }]
        : [];
      const result = await getExperimentDecision(selected.id, {
        exposure_event: decisionInputs.exposure_event,
        conversion_event: decisionInputs.conversion_event,
        guardrails,
      });
      setEventDecision(result);
    } catch (err) {
      setError(errorMessage(err, "Could not generate a decision from uploaded event data."));
    } finally {
      setDecisionLoading(false);
    }
  }

  if (loading) return <div className="panel loading-panel">Preparing experiment workspace…</div>;

  return <div className="experiment-page">
    <div className="experiment-toolbar">
      <span><FlaskConical size={14} /> EXPERIMENT INTELLIGENCE · LOCAL WORKSPACE</span>
      <button onClick={() => void load()}><RefreshCw size={14} /> Refresh</button>
    </div>
    {error && <div className="experiment-alert"><AlertTriangle size={16} />{error}</div>}
    {notice && <div className="experiment-notice"><CheckCircle2 size={16} />{notice}</div>}

    <section className="experiment-hero">
      <div className="experiment-hero-icon"><Beaker size={23} /></div>
      <span className="upload-eyebrow">FROM INSIGHT TO VALIDATION</span>
      <h2>Turn product opportunities into measurable experiments.</h2>
      <p>Generate a testable hypothesis, define success and guardrail metrics, estimate the required sample, and inspect observed results—all without paid APIs.</p>
      <div className="experiment-steps"><span>01 · Hypothesise</span><span>02 · Design</span><span>03 · Size</span><span>04 · Analyse</span></div>
    </section>

    <div className="experiment-layout">
      <section className="panel experiment-builder">
        <div className="experiment-section-heading"><div><span className="upload-eyebrow">EXPERIMENT DESIGN</span><h3>Build an experiment</h3></div><Target size={19} /></div>
        <label className="experiment-field">Start from a product opportunity
          <select value={draft.opportunity_id} onChange={(event) => void chooseOpportunity(event.target.value)}>
            <option value="">Choose an opportunity (optional)</option>
            {opportunities.map((item) => <option key={item.id} value={item.id}>{item.feature} · {item.priority}</option>)}
          </select>
        </label>
        <label className="experiment-field">Experiment name
          <input value={draft.name} onChange={(event) => edit("name", event.target.value)} placeholder="e.g. Simplify checkout flow" />
        </label>
        <label className="experiment-field">Hypothesis
          <textarea rows={3} value={draft.hypothesis} onChange={(event) => edit("hypothesis", event.target.value)} placeholder="If we…, then…, because…" />
        </label>
        <label className="experiment-field">Evidence and rationale
          <textarea rows={3} value={draft.rationale} onChange={(event) => edit("rationale", event.target.value)} placeholder="What customer and behavioural signals motivate this test?" />
        </label>
        <div className="experiment-metric-grid">
          <label className="experiment-field">Primary success metric
            <input value={draft.primary_metric} onChange={(event) => edit("primary_metric", event.target.value)} />
            <small>Choose one metric before the test begins.</small>
          </label>
          <div className="experiment-field"><span>Secondary metrics</span>
            <div className="experiment-chip-list">{draft.secondary_metrics.map((item) => <span key={item.name}>{item.name}</span>)}</div>
          </div>
        </div>
        <div className="experiment-field"><span>Guardrail metrics</span>
          <div className="experiment-guardrails">{draft.guardrails.map((item) => <div key={item.name}><CheckCircle2 size={13} /><span>{item.name}</span><small>{item.direction}</small></div>)}</div>
        </div>
        <div className="experiment-design-card">
          <h4><Beaker size={15} /> Recommended A/B design</h4>
          <div><span>Control</span><strong>Current experience</strong></div>
          <div><span>Variant</span><strong>One scoped change</strong></div>
          <div><span>Allocation</span><strong>50% / 50%</strong></div>
          <div><span>Randomisation unit</span><strong>Unique eligible user</strong></div>
          <p>Keep assignment stable at user level. Exclude internal accounts, duplicate IDs and users without a valid assignment.</p>
        </div>
      </section>

      <aside className="experiment-side">
        <section className="panel experiment-sizing">
          <span className="upload-eyebrow">SAMPLE SIZE & DURATION</span><h3>How much evidence do we need?</h3>
          <div className="experiment-input-grid">
            <label>Baseline conversion (%)<input type="number" min="0.1" max="99.9" step="0.1" value={draft.baseline_rate * 100} onChange={(event) => edit("baseline_rate", Number(event.target.value) / 100)} /></label>
            <label>Minimum detectable lift (pp)<input type="number" min="0.1" max="90" step="0.1" value={draft.minimum_detectable_effect * 100} onChange={(event) => edit("minimum_detectable_effect", Number(event.target.value) / 100)} /></label>
            <label>Daily eligible users<input type="number" min="1" step="100" value={draft.daily_eligible_users} onChange={(event) => edit("daily_eligible_users", Math.max(1, Number(event.target.value)))} /></label>
            <label>Statistical power<select value={draft.power} onChange={(event) => edit("power", Number(event.target.value))}><option value={0.8}>80%</option><option value={0.9}>90%</option></select></label>
            <label>Confidence level<select value={draft.confidence_level} onChange={(event) => edit("confidence_level", Number(event.target.value))}><option value={0.9}>90%</option><option value={0.95}>95%</option><option value={0.99}>99%</option></select></label>
          </div>
          {estimate ? <div className="experiment-estimate">
            <div><span>Users per arm</span><strong>{estimate.perArm.toLocaleString("en-IN")}</strong></div>
            <div><span>Total sample</span><strong>{estimate.total.toLocaleString("en-IN")}</strong></div>
            <div><span>Estimated days</span><strong>{estimate.days.toLocaleString("en-IN")}</strong></div>
          </div> : <p className="experiment-validation">Enter a valid baseline and lift below the 100% conversion ceiling.</p>}
          <p className="experiment-method-note">Two-proportion normal approximation, two-sided test, equal allocation. Duration uses total eligible daily traffic and excludes ramp-up or data-quality delays.</p>
        </section>
        <section className="panel experiment-save">
          <h3>Save experiment</h3><p>Store the plan in the local SQLite workspace and track its lifecycle.</p>
          <button className="experiment-primary-button" disabled={saving || !draft.name.trim() || draft.hypothesis.trim().length < 10 || !draft.primary_metric.trim() || !estimate} onClick={() => void save()}><Save size={15} />{saving ? "Saving…" : "Save experiment"}</button>
        </section>
      </aside>
    </div>

    <section className="panel experiment-list-panel">
      <div className="experiment-section-heading"><div><span className="upload-eyebrow">EXPERIMENT TRACKER</span><h3>Saved experiments</h3></div><span className="experiment-count">{experiments.length} total</span></div>
      {experiments.length ? <div className="experiment-table-wrap"><table className="experiment-table"><thead><tr><th>Experiment</th><th>Primary metric</th><th>Required / arm</th><th>Duration</th><th>Status</th><th>Update</th></tr></thead><tbody>
        {experiments.map((item) => <tr key={item.id} className={selectedId === item.id ? "selected" : ""} onClick={() => { setSelectedId(item.id); setAnalysis(null); setGuardrailInputs({}); }}>
          <td><strong>{item.name}</strong><small>{item.opportunity_title || "Standalone experiment"}</small></td><td>{item.primary_metric}</td><td>{item.sample_size_per_arm.toLocaleString("en-IN")}</td><td>{item.duration_days} days*</td><td><span className={`experiment-status status-${item.status}`}>{item.status}</span></td>
          <td><select aria-label={`Update ${item.name} status`} value={item.status} onClick={(event) => event.stopPropagation()} onChange={(event) => { setSelectedId(item.id); void setStatus(item.id, event.target.value as Experiment["status"]); }}><option value="draft">Draft</option><option value="running">Running</option><option value="completed">Completed</option><option value="archived">Archived</option></select></td>
        </tr>)}
      </tbody></table><p className="experiment-table-footnote">*Estimated from configured daily traffic. Actual runtime depends on eligibility, instrumentation, weekly cycles and operational constraints.</p></div>
      : <div className="experiment-empty"><FlaskConical size={22} /><strong>No experiments saved yet</strong><span>Choose an opportunity or write a hypothesis to create your first experiment.</span></div>}
    </section>

    <section className="panel experiment-analysis-panel">
      <div className="experiment-section-heading"><div><span className="upload-eyebrow">RESULT ANALYSIS</span><h3>Compare control and variant</h3></div><Play size={17} /></div>
      {selected && <p className="experiment-selected-label">Selected: <strong>{selected.name}</strong> · Planned sample {selected.sample_size_per_arm.toLocaleString("en-IN")} users per arm</p>}
      <div className="experiment-event-decision">
        <div>
          <span className="upload-eyebrow">EVENT-DRIVEN DECISION</span>
          <h4>Use uploaded events to recommend Ship, Iterate or Stop</h4>
          <p>Reads the latest events CSV. Exposure rows must include this experiment's ID and a control/variant assignment; conversion events are attributed to exposed users after exposure. Configure at least one guardrail event before a Ship recommendation is possible.</p>
          {selected && <small className="experiment-id-note">Experiment ID for instrumentation: {selected.id}</small>}
        </div>
        <div className="experiment-event-inputs">
          <label>Exposure event
            <input value={decisionInputs.exposure_event} onChange={(event) => setDecisionInputs((current) => ({ ...current, exposure_event: event.target.value }))} />
          </label>
          <label>Primary conversion event
            <input value={decisionInputs.conversion_event} onChange={(event) => setDecisionInputs((current) => ({ ...current, conversion_event: event.target.value }))} />
          </label>
          <label>Guardrail event (required for Ship)
            <input value={decisionInputs.guardrail_event} onChange={(event) => setDecisionInputs((current) => ({ ...current, guardrail_event: event.target.value }))} placeholder="e.g. checkout_error" />
          </label>
          <label>Allowed guardrail increase (pp)
            <input type="number" min="0" max="100" step="0.1" value={decisionInputs.guardrail_max_increase} onChange={(event) => setDecisionInputs((current) => ({ ...current, guardrail_max_increase: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} />
          </label>
        </div>
        <button className="experiment-secondary-button" disabled={!selected || decisionLoading || !decisionInputs.exposure_event.trim() || !decisionInputs.conversion_event.trim()} onClick={() => void runEventDecision()}>
          {decisionLoading ? "Reading event data…" : "Generate event-based decision"} <Play size={13} />
        </button>
        {eventDecision && <div className="experiment-decision-result">
          <div className={`experiment-decision-banner decision-${eventDecision.recommendation.toLowerCase()}`}>
            <span>RECOMMENDATION</span><strong>{eventDecision.recommendation}</strong>
          </div>
          <ul>{eventDecision.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
          <div className="experiment-decision-stats">
            <span>Control <strong>{pct(eventDecision.analysis.control.conversion_rate)}</strong> ({eventDecision.analysis.control.users.toLocaleString("en-IN")} users)</span>
            <span>Variant <strong>{pct(eventDecision.analysis.variant.conversion_rate)}</strong> ({eventDecision.analysis.variant.users.toLocaleString("en-IN")} users)</span>
            <span>Absolute lift <strong>{(eventDecision.analysis.absolute_lift * 100).toFixed(2)} pp</strong></span>
            <span>{Math.round((selected?.confidence_level ?? 0.95) * 100)}% interval <strong>{(eventDecision.analysis.difference_confidence_interval[0] * 100).toFixed(2)} to {(eventDecision.analysis.difference_confidence_interval[1] * 100).toFixed(2)} pp</strong></span>
          </div>
          <small>{eventDecision.events.exposed_users.toLocaleString("en-IN")} exposed users · {eventDecision.events.conflicting_assignment_users_excluded} conflicting assignments excluded · Planned sample {eventDecision.analysis.sample_size_reached ? "reached" : "not reached"}</small>
          {eventDecision.analysis.guardrails.length > 0 && <p>{eventDecision.guardrail_note}</p>}
          <div className="experiment-decision-limitations"><strong>Limitations</strong>{eventDecision.limitations.map((item) => <small key={item}>{item}</small>)}</div>
        </div>}
      </div>
      <div className="experiment-results-inputs">
        {(["control", "variant"] as const).map((arm) => <div className="experiment-arm" key={arm}>
          <h4>{arm === "control" ? "Control" : "Variant"}</h4>
          <label>Eligible users<input type="number" min="1" value={counts[`${arm}_users`]} onChange={(event) => setCounts((current) => ({ ...current, [`${arm}_users`]: Math.max(1, Number(event.target.value)) }))} /></label>
          <label>Primary conversions<input type="number" min="0" max={counts[`${arm}_users`]} value={counts[`${arm}_conversions`]} onChange={(event) => setCounts((current) => ({ ...current, [`${arm}_conversions`]: Math.min(current[`${arm}_users`], Math.max(0, Number(event.target.value))) }))} /></label>
        </div>)}
      </div>
      {selected?.guardrails.length ? <div className="experiment-guardrail-results"><h4>Observed guardrail rates (%)</h4>{selected.guardrails.map((guardrail) => <div className="experiment-guardrail-row" key={guardrail.name}><strong>{guardrail.name}</strong><label>Control %<input type="number" min="0" max="100" step="0.1" value={guardrailInputs[guardrail.name]?.control ?? 0} onChange={(event) => setGuardrailInputs((current) => ({ ...current, [guardrail.name]: { control: Math.min(100, Math.max(0, Number(event.target.value) || 0)), variant: current[guardrail.name]?.variant ?? 0, maxIncrease: current[guardrail.name]?.maxIncrease ?? 0 } }))} /></label><label>Variant %<input type="number" min="0" max="100" step="0.1" value={guardrailInputs[guardrail.name]?.variant ?? 0} onChange={(event) => setGuardrailInputs((current) => ({ ...current, [guardrail.name]: { control: current[guardrail.name]?.control ?? 0, variant: Math.min(100, Math.max(0, Number(event.target.value) || 0)), maxIncrease: current[guardrail.name]?.maxIncrease ?? 0 } }))} /></label><label>Allowed increase (pp)<input type="number" min="0" max="100" step="0.1" value={guardrailInputs[guardrail.name]?.maxIncrease ?? 0} onChange={(event) => setGuardrailInputs((current) => ({ ...current, [guardrail.name]: { control: current[guardrail.name]?.control ?? 0, variant: current[guardrail.name]?.variant ?? 0, maxIncrease: Math.min(100, Math.max(0, Number(event.target.value) || 0)) } }))} /></label></div>)}</div> : null}
            <button className="experiment-secondary-button" onClick={() => void runAnalysis()}>Analyse observed results <Play size={13} /></button>
      {analysis && <div className="experiment-analysis-result">
        <div className="experiment-lift-grid">
          <div><span>Control rate</span><strong>{pct(analysis.control.conversion_rate)}</strong><small>{analysis.control.conversions} / {analysis.control.users}</small></div>
          <div><span>Variant rate</span><strong>{pct(analysis.variant.conversion_rate)}</strong><small>{analysis.variant.conversions} / {analysis.variant.users}</small></div>
          <div><span>Absolute lift</span><strong>{analysis.absolute_lift >= 0 ? "+" : ""}{(analysis.absolute_lift * 100).toFixed(2)} pp</strong><small>{analysis.relative_lift_percent === null ? "Relative lift unavailable" : `${analysis.relative_lift_percent.toFixed(1)}% relative`}</small></div>
        </div>
        <div className="experiment-interval"><strong>Approx. difference interval ({Math.round((selected?.confidence_level ?? 0.95) * 100)}% confidence)</strong><span>{pct(analysis.difference_confidence_interval[0])} to {pct(analysis.difference_confidence_interval[1])}</span><small>{analysis.sample_size_reached === null ? "No planned sample attached" : analysis.sample_size_reached ? "Planned sample reached in both arms" : "Planned sample not yet reached in both arms"}</small></div>
        <p className="experiment-interpretation">{analysis.interpretation}</p>
        {analysis.guardrails.length > 0 && <div className="experiment-guardrail-output"><strong>Guardrail review</strong>{analysis.guardrails.map((item) => <div key={item.name}><span>{item.name}</span><b className={item.status === "review" ? "guardrail-risk" : "guardrail-ok"}>{item.status === "review" ? "Review regression" : "Within threshold"}</b><small>Change: {(item.absolute_change * 100).toFixed(2)} pp · Allowed: {(item.threshold * 100).toFixed(2)} pp</small></div>)}</div>}
        <p className="experiment-method-note">{analysis.methodology}</p>
      </div>}
    </section>

    <section className="experiment-caveat"><AlertTriangle size={16} /><p><strong>Decision discipline:</strong> define one primary metric before launch, monitor guardrails, avoid repeatedly checking significance and do not stop early because a result looks favourable. This result view is descriptive; validate randomisation, event quality and assumptions before rollout decisions.</p></section>
  </div>;
}

function errorMessage(error: unknown, fallback: string) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = error.response;
    if (typeof response === "object" && response !== null && "data" in response) {
      const data = response.data;
      if (typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string") return data.detail;
    }
  }
  return fallback;
}

export default ExperimentIntelligence;
