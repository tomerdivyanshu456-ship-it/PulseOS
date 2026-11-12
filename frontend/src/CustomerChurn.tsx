import { useEffect, useState } from "react";
import { RefreshCw, Users, UserRoundX, UserRoundCheck, BrainCircuit } from "lucide-react";
import { getCustomerChurn, getDatasets, type CustomerChurnResponse, type UploadedDataset } from "./services/api";
import "./CustomerChurn.css";

function CustomerChurn() {
  const [data, setData] = useState<CustomerChurnResponse | null>(null);
  const [datasets, setDatasets] = useState<UploadedDataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDatasetOptions() {
    try {
      const available = (await getDatasets()).filter((item) => item.dataset_type === "events");
      setDatasets(available);
      setSelectedDatasetId((current) => current && available.some((item) => item.id === current) ? current : "");
    } catch { setError("Could not load uploaded event datasets."); }
  }

  async function load() {
    if (!selectedDatasetId) { setError("Choose an Events dataset before running churn analysis."); return; }
    setLoading(true);
    setError("");
    try {
      setData(await getCustomerChurn(selectedDatasetId));
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

  useEffect(() => { void loadDatasetOptions(); }, []);

  const baseline = data?.model_comparison.find((item) => item.model === "Majority-class baseline");
  const predictiveModels = data?.model_comparison.filter((item) => item.model !== "Majority-class baseline") ?? [];
  const bestModelAccuracy = predictiveModels.length ? Math.max(...predictiveModels.map((item) => item.metrics.accuracy)) : null;
  const belowBaselineAccuracy = baseline !== undefined && bestModelAccuracy !== null && bestModelAccuracy < baseline.metrics.accuracy;

  if (loading) return <div className="panel churn-state">Building the historical churn cohort and evaluating models…</div>;
  return (
    <div className="churn-page">
      <div className="churn-toolbar">
        <div className="churn-dataset-picker">
          <label htmlFor="churn-dataset">Analyse this Events dataset</label>
          <select id="churn-dataset" value={selectedDatasetId} onChange={(event) => { setSelectedDatasetId(event.target.value); setData(null); setError(""); }}>
            <option value="">Choose an uploaded events dataset…</option>
            {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.original_filename} · {dataset.row_count.toLocaleString()} rows</option>)}
          </select>
          <button onClick={() => void loadDatasetOptions()} type="button">Refresh list</button>
        </div>
        <div className="churn-dataset-actions">
          {data && <p>OBSERVATION {data.observation_window.start_date} – {data.observation_window.end_date} · OUTCOME {data.outcome_window.start_date} – {data.outcome_window.end_date}</p>}
          <button onClick={() => void load()} disabled={!selectedDatasetId || loading}><RefreshCw size={14}/> {data ? "Retrain models" : "Run analysis"}</button>
        </div>
      </div>
      {error && <div className="panel churn-state churn-error"><div><strong>Churn analysis unavailable</strong><p>{error}</p></div><button onClick={() => void load()}>Try again</button></div>}
      {!data && !error && <div className="panel churn-state">{datasets.length ? "Choose an Events dataset and run the analysis." : "No Events datasets uploaded yet. Add one in Data Sources."}</div>}
      {data && <>
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
      {belowBaselineAccuracy && <section className="churn-model-warning" role="status"><strong>Model performance warning</strong><p>Neither trained model beats the majority-class baseline on holdout accuracy ({(baseline!.metrics.accuracy * 100).toFixed(1)}%). The best trained-model accuracy is {((bestModelAccuracy ?? 0) * 100).toFixed(1)}%. Review precision, recall, ROC-AUC and cross-validation before relying on these predictions. This result is a diagnostic signal, not a production-ready churn model.</p></section>}
      <section className="panel churn-section">
        <div className="churn-section-heading"><div><h3>Held-out model evaluation</h3><p>Metrics are calculated on the 25% user holdout. Positive class = churn. Compare against the majority-class baseline.</p></div><BrainCircuit size={20}/></div>
        <div className="churn-table-wrap"><table className="churn-table"><thead><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>CV F1 ± SD</th><th>CV AUC ± SD</th></tr></thead><tbody>
          {data.model_comparison.map((item) => <tr key={item.model}><td>{item.model}</td><td>{item.metrics.accuracy.toFixed(3)}</td><td>{item.metrics.precision.toFixed(3)}</td><td>{item.metrics.recall.toFixed(3)}</td><td>{item.metrics.f1.toFixed(3)}</td><td>{item.metrics.roc_auc.toFixed(3)}</td><td>{item.cross_validation ? `${item.cross_validation.f1_mean.toFixed(3)} ± ${item.cross_validation.f1_std.toFixed(3)}` : "—"}</td><td>{item.cross_validation ? `${item.cross_validation.roc_auc_mean.toFixed(3)} ± ${item.cross_validation.roc_auc_std.toFixed(3)}` : "—"}</td></tr>)}
        </tbody></table></div>
        <p className="churn-eval-note">Cross-validation uses {data.model_comparison.find((item) => item.cross_validation)?.cross_validation?.folds ?? "—"} stratified folds on the eligible cohort. Fold scores are descriptive and may be optimistic on synthetic data.</p>
      </section>
      <section className="panel churn-section">
        <div className="churn-section-heading"><div><h3>Logistic Regression confusion matrix</h3><p>Predictions on the held-out users; positive class = churn.</p></div></div>
        <div className="churn-confusion-grid">
          <div><small>True negative</small><strong>{data.confusion_matrix.true_negative}</strong><span>Correctly retained</span></div>
          <div><small>False positive</small><strong>{data.confusion_matrix.false_positive}</strong><span>Flagged, but retained</span></div>
          <div><small>False negative</small><strong>{data.confusion_matrix.false_negative}</strong><span>Missed churn</span></div>
          <div><small>True positive</small><strong>{data.confusion_matrix.true_positive}</strong><span>Correctly flagged churn</span></div>
        </div>
      </section>
      <section className="panel churn-section">
        <div className="churn-section-heading"><div><h3>Holdout user predictions</h3><p>Logistic Regression probabilities for unseen users, compared with their retrospective labels.</p></div></div>
        <div className="churn-table-wrap"><table className="churn-table"><thead><tr><th>User</th><th>Predicted churn probability</th><th>Risk band</th><th>Predicted</th><th>Observed label</th></tr></thead><tbody>
          {data.holdout_predictions.map((item) => <tr key={item.user_id}><td>{item.user_id}</td><td>{(item.predicted_churn_probability * 100).toFixed(1)}%</td><td><span className={`churn-risk ${item.risk_band.toLowerCase()}`}>{item.risk_band}</span></td><td>{item.predicted_label ? "Churn" : "Retained"}</td><td>{item.actual_churn ? "Churn" : "Retained"}</td></tr>)}
        </tbody></table></div>
      </section>
      <section className="panel churn-section"><h3>Target, features & limitations</h3><p><strong>Target definition:</strong> {data.target_definition}</p><p><strong>Features:</strong> {data.features_used.join(", ").replaceAll("_", " ")}.</p><p>{data.methodology}</p><ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
      </>}
    </div>
  );
}

export default CustomerChurn;
