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
} from "lucide-react";
import { askAnalyst, type AnalystResponse } from "./services/api";
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitQuestion(value = question) {
    const trimmed = value.trim();
    if (trimmed.length < 3 || loading) return;

    setQuestion(trimmed);
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await askAnalyst(trimmed);
      setResult(response);
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
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="analyst-page">
      <section className="analyst-hero">
        <div className="analyst-hero-icon"><BrainCircuit size={25} /></div>
        <p className="upload-eyebrow">PULSeOS INTELLIGENCE</p>
        <h2>Ask your product data anything.</h2>
        <p>Explore product behaviour and customer feedback with answers grounded in your uploaded datasets.</p>
        <div className="analyst-capabilities">
          <span><BarChart3 size={13} /> Product metrics</span>
          <span><MessageSquareText size={13} /> Customer feedback</span>
          <span><ShieldCheck size={13} /> Evidence-backed</span>
        </div>
      </section>

      <section className="analyst-composer panel">
        <label htmlFor="analyst-question">Your product question</label>
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
          placeholder="e.g. Why might customers be abandoning checkout?"
          rows={3}
          maxLength={1000}
        />
        <div className="analyst-composer-footer">
          <span>Answers use your uploaded data. Enter to submit · Shift + Enter for a new line</span>
          <button
            className="analyst-submit"
            disabled={loading || question.trim().length < 3}
            onClick={() => void submitQuestion()}
          >
            {loading ? <LoaderCircle size={15} className="analyst-spin" /> : <Search size={15} />}
            Analyse
          </button>
        </div>
      </section>

      {!result && !loading && !error && (
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
          <span>Reviewing available metrics, feedback and supporting evidence.</span>
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
          <div className="analyst-question-label">YOUR QUESTION</div>
          <h3 className="analyst-question-title">{result.question}</h3>

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
                      {finding.type === "metric" ? "PRODUCT METRIC" : "CUSTOMER FEEDBACK"}
                    </span>
                    <h4>{finding.title}</h4>
                    <p>{finding.detail}</p>
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
                <div key={source.name}>
                  <strong>{source.name}</strong><span>{source.detail}</span>
                </div>
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
