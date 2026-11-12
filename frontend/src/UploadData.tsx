
import { useEffect, useState } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Eye,
  RefreshCw,
} from "lucide-react";
import {
  uploadDataset,
  getDatasets,
  getDatasetPreview,
} from "./services/api";
import "./UploadData.css";

type Dataset = {
  id: string;
  dataset_type: string;
  original_filename: string;
  row_count: number;
  uploaded_at: string;
};

type UploadType = "events" | "reviews";

function UploadData() {
  const [files, setFiles] = useState<Record<UploadType, File | null>>({
    events: null,
    reviews: null,
  });

  const [loading, setLoading] = useState<UploadType | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function loadDatasets() {
    setRefreshing(true);
    try {
      const data = await getDatasets();
      setDatasets(data);
    } catch {
      setError("Could not load dataset history.");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDatasets();
  }, []);

  function selectFile(type: UploadType, file?: File) {
    setMessage("");
    setError("");
    setPreview(null);

    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setError("File size must not exceed 20 MB.");
      return;
    }

    setFiles((previous) => ({
      ...previous,
      [type]: file,
    }));
  }

  async function handleUpload(type: UploadType) {
    const file = files[type];

    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    setLoading(type);
    setMessage("");
    setError("");
    setPreview(null);

    try {
      const result = await uploadDataset(type, file);

      setMessage(
        `${result.data.filename} uploaded successfully. ${result.data.rows} records validated.`
      );

      setFiles((previous) => ({
        ...previous,
        [type]: null,
      }));

      await loadDatasets();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Upload failed. Please check your CSV and try again."
      );
    } finally {
      setLoading(null);
    }
  }

  async function handlePreview(datasetId: string) {
    setError("");
    setMessage("");

    try {
      const data = await getDatasetPreview(datasetId);
      setPreview(data);
    } catch {
      setError("Could not retrieve the dataset preview.");
    }
  }

  return (
    <div className="upload-page">
      <div className="upload-heading">
        <div>
          <p className="upload-eyebrow">DATA MANAGEMENT</p>
          <h2>Upload your data</h2>
          <p>
            Import product behaviour and customer feedback
            to generate product intelligence.
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={loadDatasets}
          disabled={refreshing}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {message && (
        <div className="upload-message success-message">
          <CheckCircle size={18} />
          {message}
        </div>
      )}

      {error && (
        <div className="upload-message error-message">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      <div className="upload-cards">
        <div className="upload-card">
          <div className="upload-card-icon">
            <FileSpreadsheet size={23} />
          </div>

          <h3>User Behaviour Data</h3>
          <p>
            Upload events such as product views, clicks,
            cart additions and purchases.
          </p>

          <label className="file-picker">
            <UploadCloud size={19} />
            Choose CSV file
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) =>
                selectFile("events", e.target.files?.[0])
              }
            />
          </label>

          <div className="selected-file">
            {files.events?.name || "No file selected"}
          </div>

          <button
            className="upload-button"
            disabled={!files.events || loading !== null}
            onClick={() => handleUpload("events")}
          >
            {loading === "events" ? "Uploading..." : "Upload Events"}
          </button>

          <small>
            Required columns: user_id, event_name, timestamp
          </small>
        </div>

        <div className="upload-card">
          <div className="upload-card-icon">
            <FileSpreadsheet size={23} />
          </div>

          <h3>Customer Reviews</h3>
          <p>
            Upload customer ratings and written feedback
            to discover recurring problems.
          </p>

          <label className="file-picker">
            <UploadCloud size={19} />
            Choose CSV file
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) =>
                selectFile("reviews", e.target.files?.[0])
              }
            />
          </label>

          <div className="selected-file">
            {files.reviews?.name || "No file selected"}
          </div>

          <button
            className="upload-button"
            disabled={!files.reviews || loading !== null}
            onClick={() => handleUpload("reviews")}
          >
            {loading === "reviews" ? "Uploading..." : "Upload Reviews"}
          </button>

          <small>
            Required columns: review_id, rating, review_text
          </small>
        </div>
      </div>

      <section className="dataset-history">
        <div className="history-heading">
          <div>
            <h3>Uploaded datasets</h3>
            <p>Your locally stored dataset history</p>
          </div>
          <span>{datasets.length} datasets</span>
        </div>

        {datasets.length === 0 ? (
          <div className="history-empty">
            No datasets uploaded yet.
          </div>
        ) : (
          <div className="history-table">
            <div className="history-row history-header">
              <span>Filename</span>
              <span>Type</span>
              <span>Records</span>
              <span>Action</span>
            </div>

            {datasets.map((dataset) => (
              <div className="history-row" key={dataset.id}>
                <span className="filename-cell">
                  <FileSpreadsheet size={17} />
                  {dataset.original_filename}
                </span>
                <span>
                  {dataset.dataset_type === "events"
                    ? "Behaviour"
                    : "Reviews"}
                </span>
                <span>{dataset.row_count}</span>
                <button
                  className="preview-button"
                  onClick={() => handlePreview(dataset.id)}
                >
                  <Eye size={15} />
                  Preview
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {preview && (
        <section className="dataset-history preview-section">
          <div className="history-heading">
            <div>
              <h3>{preview.filename}</h3>
              <p>
                Showing up to 10 records out of {preview.total_rows}
              </p>
            </div>
            <button
              className="preview-button"
              onClick={() => setPreview(null)}
            >
              Close preview
            </button>
          </div>

          <div className="preview-table">
            <table>
              <thead>
                <tr>
                  {Object.keys(preview.preview[0] || {}).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview.map((row: any, index: number) => (
                  <tr key={index}>
                    {Object.keys(preview.preview[0] || {}).map((key) => (
                      <td key={key}>{String(row[key] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default UploadData;
