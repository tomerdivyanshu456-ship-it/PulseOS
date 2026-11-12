import { useEffect, useState } from "react";
import {
  AlertCircle,
  FileText,
  MessageSquareText,
  RefreshCw,
  Star,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getVoiceOfCustomer,
  type VoiceOfCustomerOverview,
} from "./services/api";
import "./VoiceOfCustomer.css";

const sentimentColors: Record<string, string> = {
  Positive: "#22a06b",
  Neutral: "#e2a53b",
  Negative: "#dc6262",
};

function VoiceOfCustomer() {
  const [data, setData] = useState<VoiceOfCustomerOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAnalysis() {
    setLoading(true);
    setError("");
    try {
      const result = await getVoiceOfCustomer();
      setData(result);
    } catch (err: unknown) {
      setData(null);
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
          : "Could not load customer feedback. Check the backend and uploaded reviews dataset.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnalysis();
  }, []);

  if (loading) {
    return <div className="panel voc-state">Analysing customer feedback…</div>;
  }

  if (error || !data) {
    return (
      <div className="panel voc-empty">
        <AlertCircle size={30} />
        <h3>No customer feedback analysis available</h3>
        <p>{error || "Upload a reviews CSV to begin."}</p>
        <div className="voc-actions">
          <button className="voc-primary" onClick={loadAnalysis}>
            <RefreshCw size={15} /> Try again
          </button>
        </div>
      </div>
    );
  }

  const positive = data.sentiment_distribution.find((item) => item.sentiment === "Positive")?.count ?? 0;
  const negative = data.sentiment_distribution.find((item) => item.sentiment === "Negative")?.count ?? 0;

  return (
    <div className="voc-page">
      <div className="voc-heading">
        <div>
          <p className="upload-eyebrow">VOICE OF CUSTOMER</p>
          <h2>Understand your customers</h2>
          <p>Explore review sentiment, recurring themes and the feedback behind them.</p>
        </div>
        <button className="refresh-button" onClick={loadAnalysis}>
          <RefreshCw size={15} /> Refresh analysis
        </button>
      </div>

      <div className="voc-source">
        <FileText size={15} />
        <span>Source: {data.filename}</span>
        <span>{data.total_reviews.toLocaleString("en-IN")} reviews analysed</span>
      </div>

      <div className="voc-metrics">
        <div className="voc-metric">
          <div className="voc-metric-label"><MessageSquareText size={17} /> Total reviews</div>
          <strong>{data.total_reviews.toLocaleString("en-IN")}</strong>
          <span>Valid customer records</span>
        </div>
        <div className="voc-metric">
          <div className="voc-metric-label"><Star size={17} /> Average rating</div>
          <strong>{data.average_rating.toFixed(2)} / 5</strong>
          <span>Mean submitted rating</span>
        </div>
        <div className="voc-metric">
          <div className="voc-metric-label"><ThumbsUp size={17} /> Positive feedback</div>
          <strong>{positive}</strong>
          <span>{((positive / data.total_reviews) * 100).toFixed(1)}% of reviews</span>
        </div>
        <div className="voc-metric">
          <div className="voc-metric-label"><ThumbsDown size={17} /> Negative feedback</div>
          <strong>{negative}</strong>
          <span>{((negative / data.total_reviews) * 100).toFixed(1)}% of reviews</span>
        </div>
      </div>

      <div className="voc-chart-grid">
        <section className="panel voc-chart-panel">
          <div className="panel-heading">
            <div>
              <h3>Sentiment distribution</h3>
              <p>Positive, neutral and negative review classification</p>
            </div>
          </div>
          <div className="voc-pie-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.sentiment_distribution}
                  dataKey="count"
                  nameKey="sentiment"
                  cx="50%"
                  cy="50%"
                  innerRadius={58}
                  outerRadius={88}
                  paddingAngle={3}
                >
                  {data.sentiment_distribution.map((entry) => (
                    <Cell key={entry.sentiment} fill={sentimentColors[entry.sentiment]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [value, "Reviews"]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="voc-legend">
              {data.sentiment_distribution.map((item) => (
                <div key={item.sentiment}>
                  <span className="voc-legend-dot" style={{ background: sentimentColors[item.sentiment] }} />
                  <span>{item.sentiment}</span>
                  <strong>{item.count}</strong>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel voc-chart-panel">
          <div className="panel-heading">
            <div>
              <h3>Rating breakdown</h3>
              <p>Number of reviews for each star rating</p>
            </div>
          </div>
          <div className="voc-rating-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.rating_distribution} margin={{ top: 12, right: 10, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf0f5" />
                <XAxis dataKey="rating" tickFormatter={(value) => `${value}★`} tick={{ fill: "#8791a4", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "#8791a4", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(value) => [value, "Reviews"]} labelFormatter={(value) => `${value} star rating`} />
                <Bar dataKey="count" fill="#786be9" radius={[5, 5, 0, 0]} barSize={34} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="panel voc-topics">
        <div className="panel-heading">
          <div>
            <h3>Recurring customer pain points</h3>
            <p>TF-IDF terms grouped into themes from negative reviews</p>
          </div>
          <span className="chart-tag">{data.topics.length} themes</span>
        </div>
        {data.topics.length === 0 ? (
          <div className="voc-no-topics">No recurring negative themes were found in this dataset.</div>
        ) : (
          <div className="voc-topic-grid">
            {data.topics.map((topic, index) => (
              <article className="voc-topic-card" key={`${topic.label}-${index}`}>
                <div className="voc-topic-number">THEME 0{index + 1}</div>
                <h4>{topic.label}</h4>
                <div className="voc-keywords">
                  {topic.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}
                </div>
                <p className="voc-topic-count">{topic.review_count} review(s) associated with this theme</p>
                <blockquote>“{topic.evidence}”</blockquote>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel voc-evidence">
        <div className="panel-heading">
          <div>
            <h3>Customer evidence</h3>
            <p>Original negative reviews supporting the analysis</p>
          </div>
          <span className="chart-tag">{data.negative_evidence.length} reviews</span>
        </div>
        {data.negative_evidence.length === 0 ? (
          <div className="voc-no-topics">No negative reviews in the selected dataset.</div>
        ) : (
          <div className="voc-review-list">
            {data.negative_evidence.map((review, index) => (
              <article className="voc-review" key={index}>
                <div className="voc-review-rating">{review.rating} ★</div>
                <p>“{review.review_text}”</p>
                <span>Classified as {review.sentiment}</span>
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="voc-method-note">
        <strong>Methodology and limitations</strong>
        <p>{data.methodology.sentiment} {data.methodology.topics} These are lightweight, explainable techniques; sentiment labels and topic groupings should be reviewed against the original feedback before making product decisions.</p>
      </div>
    </div>
  );
}

export default VoiceOfCustomer;
