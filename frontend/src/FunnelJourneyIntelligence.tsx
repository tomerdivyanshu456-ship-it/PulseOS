import { useEffect, useState } from "react";
import { Activity, GitBranch, Plus, RefreshCw, Route, Trash2, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getJourneyIntelligence, type JourneyIntelligenceResponse } from "./services/api";
import "./FunnelJourneyIntelligence.css";

function FunnelJourneyIntelligence() {
  const [data, setData] = useState<JourneyIntelligenceResponse | null>(null);
  const [steps, setSteps] = useState<string[]>([]);
  const [dimension, setDimension] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(selectedSteps?: string[], selectedDimension?: string) {
    setLoading(true);
    setError("");
    try {
      const result = await getJourneyIntelligence(selectedSteps, selectedDimension);
      setData(result);
      if (!selectedSteps) setSteps(result.steps);
      if (!selectedDimension) setDimension(result.selected_dimension || "");
    } catch (err: unknown) {
      const message =
        typeof err === "object" && err !== null && "response" in err &&
        typeof err.response === "object" && err.response !== null &&
        "data" in err.response && typeof err.response.data === "object" &&
        err.response.data !== null && "detail" in err.response.data &&
        typeof err.response.data.detail === "string"
          ? err.response.data.detail
          : "Unable to calculate journey intelligence. Check the backend and uploaded event data.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function updateStep(index: number, value: string) {
    setSteps((current) => current.map((step, stepIndex) => stepIndex === index ? value : step));
  }

  const unusedEvents = (data?.event_catalog || []).filter(
    (event) => !steps.includes(event.event_name)
  );

  return (
    <div className="journey-page">
      <div className="journey-toolbar">
        <p>Explore ordered conversion, friction points and common event paths.</p>
        <button onClick={() => void load(steps, dimension || undefined)} disabled={loading}>
          <RefreshCw size={14} /> Refresh analysis
        </button>
      </div>

      {loading && !data ? <div className="panel loading-panel">Analysing event journeys…</div> : null}
      {error ? <div className="panel journey-error">{error}<button onClick={() => void load(steps, dimension || undefined)}>Try again</button></div> : null}

      {data?.status === "insufficient_events" ? (
        <div className="panel journey-empty">
          <Route size={24} />
          <strong>Not enough event types to build a funnel</strong>
          <p>{data.methodology}</p>
          <small>Upload an event CSV containing at least two distinct event names.</small>
        </div>
      ) : data?.status === "ready" ? (
        <>
          <section className="journey-intro">
            <span className="upload-eyebrow">FUNNEL & JOURNEY INTELLIGENCE</span>
            <h2>Find where users progress, hesitate and leave.</h2>
            <p>Build an ordered funnel from your tracked events, then inspect the most common paths through your product.</p>
            <small>Observed period: {data.period?.start_date || "—"} to {data.period?.end_date || "—"} · Analysis unit: {data.unit}</small>
          </section>

          <section className="panel journey-builder">
            <div className="journey-section-heading">
              <div><h3>Configure your funnel</h3><p>Choose 2–6 events in the order users should complete them.</p></div>
              <GitBranch size={19} />
            </div>
            <div className="journey-step-builder">
              {steps.map((step, index) => (
                <div className="journey-step-control" key={index}>
                  <span>{index + 1}</span>
                  <select value={step} onChange={(event) => updateStep(index, event.target.value)}>
                    {data.event_catalog.map((event) => (
                      <option value={event.event_name} key={event.event_name}
                        disabled={steps.includes(event.event_name) && event.event_name !== step}>
                        {event.event_name} ({event.event_count})
                      </option>
                    ))}
                  </select>
                  {steps.length > 2 && <button aria-label={`Remove step ${index + 1}`} onClick={() => setSteps((current) => current.filter((_, i) => i !== index))}><Trash2 size={14} /></button>}
                </div>
              ))}
              <div className="journey-builder-actions">
                <button className="journey-secondary-button" disabled={steps.length >= 6 || unusedEvents.length === 0}
                  onClick={() => setSteps((current) => [...current, unusedEvents[0].event_name])}>
                  <Plus size={14} /> Add step
                </button>
                <label>Compare by
                  <select value={dimension} onChange={(event) => setDimension(event.target.value)}>
                    <option value="">No segment comparison</option>
                    {data.dimensions.map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}
                  </select>
                </label>
                <button className="journey-primary-button" disabled={loading || steps.length < 2}
                  onClick={() => void load(steps, dimension || undefined)}>Analyse journey</button>
              </div>
            </div>
          </section>

          <section className="journey-summary-grid">
            <article className="panel journey-summary-card"><Users size={17} /><span>Units analysed</span><strong>{(data.total_units ?? 0).toLocaleString()}</strong><small>{data.unit} in the uploaded dataset</small></article>
            <article className="panel journey-summary-card"><Activity size={17} /><span>Entry units</span><strong>{(data.funnel[0]?.units_reached || 0).toLocaleString()}</strong><small>Reached the first selected event</small></article>
            <article className="panel journey-summary-card"><Route size={17} /><span>Completed funnel</span><strong>{(data.funnel[data.funnel.length - 1]?.conversion_from_entry || 0).toFixed(1)}%</strong><small>Of units reaching the entry step</small></article>
          </section>

          <section className="panel journey-section">
            <div className="journey-section-heading"><div><h3>Ordered funnel & drop-off</h3><p>Each unit must reach each selected event after the preceding event within the same session (or user when sessions are unavailable).</p></div><GitBranch size={19} /></div>
            <div className="journey-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.funnel} layout="vertical" margin={{ top: 4, right: 18, left: 10, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#edf0f5" />
                  <XAxis type="number" allowDecimals={false} tick={{ fill: "#8791a4", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="event_name" width={125} tick={{ fill: "#697386", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(value) => [value, "Units reached"]} />
                  <Bar dataKey="units_reached" fill="#786be9" radius={[0, 5, 5, 0]} barSize={22} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="journey-funnel-table-wrap">
              <table className="journey-table">
                <thead><tr><th>Step</th><th>Units reached</th><th>Drop-off</th><th>Step conversion</th><th>Entry conversion</th></tr></thead>
                <tbody>{data.funnel.map((item) => <tr key={item.event_name}><td><strong>{item.step}. {item.event_name}</strong></td><td>{item.units_reached.toLocaleString()}</td><td>{item.drop_off_units.toLocaleString()} ({item.drop_off_rate.toFixed(1)}%)</td><td>{item.conversion_from_previous.toFixed(1)}%</td><td>{item.conversion_from_entry.toFixed(1)}%</td></tr>)}</tbody>
              </table>
            </div>
          </section>

          <section className="panel journey-section">
            <div className="journey-section-heading"><div><h3>Most common event paths</h3><p>Observed event sequences, with consecutive duplicate event names collapsed and paths capped at six events.</p></div><Route size={19} /></div>
            {data.journey_paths.length ? <div className="journey-path-list">{data.journey_paths.map((path) => <div className="journey-path-row" key={path.path}><div><strong>{path.path}</strong><small>{path.units.toLocaleString()} {data.unit}</small></div><span>{path.share.toFixed(1)}%</span></div>)}</div> : <p className="journey-footnote">No event paths are available.</p>}
          </section>

          {data.segment_funnels.length > 0 && (
            <section className="panel journey-section">
              <div className="journey-section-heading"><div><h3>Funnel comparison by segment</h3><p>Compares the same ordered funnel across users' most frequently observed attribute values.</p></div><Users size={19} /></div>
              <div className="journey-funnel-table-wrap"><table className="journey-table">
                <thead><tr><th>Segment</th><th>Units</th>{data.steps.map((step) => <th key={step}>{step}</th>)}</tr></thead>
                <tbody>{data.segment_funnels.map((segment) => <tr key={segment.segment}><td><strong>{segment.segment}</strong></td><td>{segment.units.toLocaleString()}</td>{segment.funnel.map((item) => <td key={item.event_name}>{item.units_reached.toLocaleString()}</td>)}</tr>)}</tbody>
              </table></div>
            </section>
          )}

          <p className="journey-footnote">{data.methodology}</p>
        </>
      ) : null}
    </div>
  );
}

export default FunnelJourneyIntelligence;
