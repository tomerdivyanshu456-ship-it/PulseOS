import { useEffect, useState } from "react";
import { RefreshCw, Users, UserRoundX, UserRoundCheck, BrainCircuit } from "lucide-react";
import { getCustomerChurn, type CustomerChurnResponse } from "./services/api";
import "./CustomerChurn.css";

function CustomerChurn() {
  const [data, setData] = useState<CustomerChurnResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await getCustomerChurn());
    } catch (err: unknown) {
      const detail = typeof err === "object" && err !== null && "response" in err &&
        typeof err.response === "object" && err.response !== null && "data" in err.response &&
        typeof err.response.data === "object" && err.response.data !== null && "detail" in err.response.data
        ? String(err.response.data.detail)
        : "Unable to train churn models. Check the uploaded event dataset.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  if (loading) return <div className="panel churn-state">Building the historical churn cohort and evaluating models…</div>;
  if (error || !data) return (
    <div className="panel churn-state churn-error">
      <div><strong>Churn model unavailable</strong><p>{error || "No churn results are available."}</p></div>
      <button onClick={() => void load()}>Try again</button>
    </div>
  );

  return (
    <div className="churn-page">
      <div className="churn-toolbar">
        <p>SUPERVISED ML · OBSERVATION {data.observation_window.start_date} – {data.observation_window.end_date} · OUTCOME {data.outcome_window.start_date} – {data.outcome_window.end_date}</p>
        <button onClick={() => void load()}><RefreshCw size={14}/> Retrain models</button>
      </div>
      <section className="churn-intro">
        <span className="upload-eyebrow">CUSTOMER CHURN PREDICTION</span>
        <h2>Identify behavioural patterns associated with churn.</h2>
        <p>Two supervised classifiers learn from a historical 7-day activity window and are evaluated on users they did not train on.</p>
      </section>
      <section className="churn-summary-grid">
        <article className="panel"><Users size={18}/><span>Eligible users</span><strong>{data.cohort_size.toLocaleString("en-IN")}</strong><small>{data.train_users} train · {data.holdout_users} holdout</small></article>
        <article className="panel"><UserRoundX size={18}/><span>Churned by inactivity</span><strong>{data.churned_users.toLocaleString("en-IN")}</strong><small>No events in the following 7 days</small></article>
        <article className="panel"><UserRoundCheck size={18}/><span>Retained</span><strong>{data.retained_users.toLocaleString("en-IN")}</strong><small>At least one event in the outcome window</small></article>
      </section>
      <section className="panel churn-section">
        <div className="churn-section-heading"><div><h3>Held-out model evaluation</h3><p>Metrics are calculated on the 25% user holdout. Positive class = churn.</p></div><BrainCircuit size={20}/></div>
        <div className="churn-table-wrap"><table className="churn-table"><thead><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th></tr></thead><tbody>
          {data.model_comparison.map((item) => <tr key={item.model}><td>{item.model}</td><td>{item.metrics.accuracy.toFixed(3)}</td><td>{item.metrics.precision.toFixed(3)}</td><td>{item.metrics.recall.toFixed(3)}</td><td>{item.metrics.f1.toFixed(3)}</td><td>{item.metrics.roc_auc.toFixed(3)}</td></tr>)}
        </tbody></table></div>
      </section>
      <section className="panel churn-section">
        <div className="churn-section-heading"><div><h3>Holdout user predictions</h3><p>Logistic Regression probabilities for unseen users, compared with their retrospective labels.</p></div></div>
        <div className="churn-table-wrap"><table className="churn-table"><thead><tr><th>User</th><th>Predicted churn probability</th><th>Risk band</th><th>Predicted</th><th>Observed label</th></tr></thead><tbody>
          {data.holdout_predictions.map((item) => <tr key={item.user_id}><td>{item.user_id}</td><td>{(item.predicted_churn_probability * 100).toFixed(1)}%</td><td><span className={`churn-risk ${item.risk_band.toLowerCase()}`}>{item.risk_band}</span></td><td>{item.predicted_label ? "Churn" : "Retained"}</td><td>{item.actual_churn ? "Churn" : "Retained"}</td></tr>)}
        </tbody></table></div>
      </section>
      <section className="panel churn-section"><h3>Target, features & limitations</h3><p><strong>Target definition:</strong> {data.target_definition}</p><p><strong>Features:</strong> {data.features_used.join(", ").replaceAll("_", " ")}.</p><p>{data.methodology}</p><ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </div>
  );
}

export default CustomerChurn;
