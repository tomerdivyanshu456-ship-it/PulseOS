import { useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  BrainCircuit,
  LoaderCircle,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import {
  askAnalyst,
  type AnalystConversationTurn,
  type AnalystResponse,
} from "./services/api";
import "./AIAnalyst.css";

const suggestedQuestions = [
  "Why might customers be abandoning checkout?",
  "What are the biggest customer pain points?",
  "Are app crashes affecting product engagement?",
  "Give me an overall product health summary.",
];

function AIAnalyst() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AnalystResponse | null>(null);
  const [history, setHistory] = useState<AnalystConversationTurn[]>([]);
  const [transcript, setTranscript] = useState<AnalystConversationTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitQuestion(value = question) {
    const trimmed = value.trim();
    if (trimmed.length < 3 || loading) return;

    const nextHistory = history.slice(-8);
    setQuestion("");
    setLoading(true);
    setError("");
    setResult(null);
    setTranscript((current) => [...current, { role: "user", content: trimmed }]);

    try {
      const response = await askAnalyst(trimmed, nextHistory);
      setResult(response);
      setHistory((current) => {
        const updated: AnalystConversationTurn[] = [
          ...current,
          { role: "user" as const, content: trimmed },
          { role: "assistant" as const, content: response.answer },
        ];
        return updated.slice(-8);
      });
      setTranscript((current) => [
        ...current,
        { role: "assistant", content: response.answer },
      ]);
    } catch (err: unknown) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof err.response === "object" &&
        err.response !== null &&
        "data" in err.response &&
        typeof err.response.data === "object" &&
        err.response.data !== null &&
        "detail" in err.response.data &&
        typeof err.response.data.detail === "string"
          ? err.response.data.detail
          : "Unable to reach the analyst. Check that the backend is running.";
      setError(detail);
      setTranscript((current) => current.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }

  function startNewAnalysis() {
    setQuestion("");
    setResult(null);
    setHistory([]);
    setTranscript([]);
    setError("");
  }

  return (
    <div className="analyst-page">
      <section className="analyst-hero">
        <div className="analyst-hero-icon"><BrainCircuit size={25} /></div>
        <p className="upload-eyebrow">PULSEOS INTELLIGENCE</p>
        <h2>Ask your product data anything.</h2>
        <p>Explore product behaviour and customer feedback with answers grounded in your uploaded datasets.</p>
        <div className="analyst-capabilities">
          <span><BarChart3 size={13} /> Product metrics</span>
          <span><MessageSquareText size={13} /> Customer feedback</span>
          <span><ShieldCheck size={13} /> Evidence-backed</span>
        </div>
      </section>

      <section className="analyst-composer panel">
        <label htmlFor="analyst-question">{history.length ? "Ask a follow-up question" : "Your product question"}</label>
        <textarea
          id="analyst-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submitQuestion();
            }
          }}
          placeholder={history.length ? "e.g. What should we investigate first?" : "e.g. Why might customers be abandoning checkout?"}
          rows={3}
          maxLength={1000}
        />
        <div className="analyst-composer-footer">
          <span>Enter to submit · Shift + Enter for a new line</span>
          <div className="analyst-composer-actions">
            {history.length > 0 && <button className="analyst-reset" onClick={startNewAnalysis}>New analysis</button>}
            <button className="analyst-submit" disabled={loading || question.trim().length < 3} onClick={() => void submitQuestion()}>
              {loading ? <LoaderCircle size={15} className="analyst-spin" /> : <Search size={15} />}
              Analyse
            </button>
          </div>
        </div>
      </section>

      {transcript.length > 0 && (
        <section className="analyst-conversation">
          <div className="analyst-conversation-heading">
            <h3>Conversation</h3>
            <span>Recent context is used for follow-up questions</span>
          </div>
          {transcript.map((turn, index) => (
            <article className={turn.role === "user" ? "analyst-turn user" : "analyst-turn assistant"} key={index}>
              <strong>{turn.role === "user" ? "You" : "PulseOS Analyst"}</strong>
              <p>{turn.content}</p>
            </article>
          ))}
        </section>
      )}

      {!result && !loading && !error && history.length === 0 && (
        <section className="analyst-suggestions">
          <h3><Sparkles size={16} /> Suggested questions</h3>
          <div className="analyst-suggestion-grid">
            {suggestedQuestions.map((item) => (
              <button key={item} onClick={() => void submitQuestion(item)}>
                <span>{item}</span><ArrowUpRight size={15} />
              </button>
            ))}
          </div>
        </section>
      )}

      {loading && (
        <div className="panel analyst-loading">
          <LoaderCircle size={22} className="analyst-spin" />
          <strong>Analysing your product data…</strong>
          <span>Reviewing available metrics, feedback and conversation context.</span>
        </div>
      )}

      {error && (
        <div className="panel analyst-error">
          <AlertTriangle size={20} />
          <div><strong>Analysis unavailable</strong><p>{error}</p></div>
        </div>
      )}

      {result && (
        <section className="analyst-results">
          <div className="analyst-result-heading">
            <div>
              <div className="analyst-question-label">LATEST ANALYSIS</div>
              <h3 className="analyst-question-title">{result.question}</h3>
            </div>
            {result.context_used && <span className="analyst-context-badge">Follow-up context used</span>}
          </div>

          {result.funnel_analysis && (
            <section className="panel analyst-funnel">
              <div className="analyst-section-title"><BarChart3 size={17} /> Sequential funnel analysis</div>
              <div className="analyst-funnel-stages">
                {result.funnel_analysis.stages.map((stage, index) => (
                  <div className="analyst-funnel-stage" key={stage.stage}>
                    <span>{stage.stage}</span>
                    <strong>{stage.count}</strong>
                    {index === 0 && <small>Starting stage</small>}
                    {index === 1 && <small>{result.funnel_analysis?.conversion_rates.view_to_cart}% from view</small>}
                    {index === 2 && <small>{result.funnel_analysis?.conversion_rates.cart_to_purchase}% from cart</small>}
                  </div>
                ))}
              </div>
              <p className="analyst-funnel-note">{result.funnel_analysis.unit} · {result.funnel_analysis.reliability_note}</p>
            </section>
          )}

          {result.priority_matrix && result.priority_matrix.length > 0 && (
            <section className="panel analyst-priority-panel">
              <div className="analyst-section-title"><Target size={17} /> Priority matrix</div>
              <p className="analyst-priority-intro">Issues are positioned by estimated severity and evidence strength. This is a triage aid, not a measure of business impact.</p>
              <div className="analyst-matrix-layout">
                <div className="analyst-matrix-y-label">Evidence strength</div>
                <div className="analyst-matrix">
                  <div className="analyst-matrix-quadrant q-top-left"><span>Validate severity</span></div>
                  <div className="analyst-matrix-quadrant q-top-right"><span>Investigate first</span></div>
                  <div className="analyst-matrix-quadrant q-bottom-left"><span>Monitor</span></div>
                  <div className="analyst-matrix-quadrant q-bottom-right"><span>Gather more evidence</span></div>
                  {result.priority_matrix.map((item, index) => (
                    <div
                      className="analyst-matrix-dot"
                      key={item.label}
                      style={{
                        left: `${Math.max(5, Math.min(95, item.severity_score))}%`,
                        bottom: `${Math.max(5, Math.min(95, item.evidence_strength))}%`,
                        transform: `translate(calc(-50% + ${(index - (result.priority_matrix.length - 1) / 2) * 13}px), 50%)`,
                      }}
                      title={`${index + 1}. ${item.label}: severity ${item.severity_score}/100, evidence ${item.evidence_strength}/100`}
                      aria-label={`${index + 1}. ${item.label}`}
                    >
                      {index + 1}
                    </div>
                  ))}
                </div>
              </div>
              <div className="analyst-matrix-x-label">Issue severity →</div>
              <div className="analyst-priority-list">
                {result.priority_matrix.map((item, index) => (
                  <div className="analyst-priority-item" key={item.label}>
                    <div>
                      <strong><span className="analyst-priority-index">{index + 1}</span>{item.label}</strong>
                      <span>{item.review_count} negative review(s) · {item.average_rating}/5 rating · {item.evidence_label}</span>
                    </div>
                    <div className="analyst-priority-scores">
                      <b>{item.priority_score}/100</b>
                      <small>{item.quadrant}</small>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <article className="panel analyst-answer">
            <div className="analyst-section-title"><Sparkles size={17} /> Analyst response</div>
            <p>{result.answer}</p>
          </article>

          {result.findings.length > 0 && (
            <section className="analyst-section">
              <h3>Key findings</h3>
              <div className="analyst-findings-grid">
                {result.findings.map((finding, index) => (
                  <article className="panel analyst-finding" key={finding.title + index}>
                    <span className={finding.type === "metric" ? "analyst-finding-type metric" : "analyst-finding-type feedback"}>
                      {finding.type === "metric" ? "OBSERVED METRIC" : "CUSTOMER FEEDBACK"}
                    </span>
                    <h4>{finding.title}</h4>
                    <p>{finding.detail}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {result.recommendations.length > 0 && (
            <section className="analyst-section">
              <h3><Target size={16} /> Recommended next actions</h3>
              <div className="analyst-recommendations">
                {result.recommendations.map((item, index) => (
                  <article className="panel analyst-recommendation" key={item.title + index}>
                    <div className="analyst-recommendation-number">ACTION 0{index + 1}</div>
                    <h4>{item.title}</h4>
                    <div><strong>Suggested action</strong><p>{item.action}</p></div>
                    <div><strong>Why this matters</strong><p>{item.rationale}</p></div>
                    <div><strong>How to validate</strong><p>{item.validation}</p></div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {result.evidence.length > 0 && (
            <section className="panel analyst-evidence">
              <div className="analyst-section-title"><MessageSquareText size={17} /> Supporting customer evidence</div>
              {result.evidence.map((item, index) => (
                <blockquote key={index}>
                  <span>{item.rating} ★ · {item.sentiment}</span>
                  <p>“{item.text}”</p>
                </blockquote>
              ))}
            </section>
          )}

          {result.sources.length > 0 && (
            <section className="panel analyst-sources">
              <h3>Data sources used</h3>
              {result.sources.map((source) => (
                <div key={source.name}><strong>{source.name}</strong><span>{source.detail}</span></div>
              ))}
            </section>
          )}

          {result.limitations.length > 0 && (
            <section className="analyst-limitations">
              <div><AlertTriangle size={16} /><strong>Limitations and interpretation</strong></div>
              <ul>{result.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
            </section>
          )}
        </section>
      )}
    </div>
  );
}

export default AIAnalyst;
