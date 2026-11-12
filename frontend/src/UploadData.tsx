import { useEffect, useState } from "react";
import {
  UploadCloud, FileSpreadsheet, FileText, CheckCircle, AlertCircle,
  Eye, RefreshCw, ArrowRight, Loader2,
} from "lucide-react";
import {
  uploadDataset, uploadDocument, inspectDataset, getDatasets,
  getDatasetPreview,
} from "./services/api";
import type { DatasetInspection } from "./services/api";
import "./UploadData.css";

type Dataset = {
  id: string;
  dataset_type: string;
  original_filename: string;
  row_count: number;
  uploaded_at: string;
};
type UploadType = "events" | "reviews";
const REQUIRED: Record<UploadType, Array<{ key: string; label: string }>> = {
  events: [
    { key: "user_id", label: "User ID" },
    { key: "event_name", label: "Event name" },
    { key: "timestamp", label: "Timestamp" },
  ],
  reviews: [
    { key: "review_id", label: "Review ID" },
    { key: "rating", label: "Rating (1–5)" },
    { key: "review_text", label: "Review text" },
  ],
};

function UploadData() {
  const [tabularFile, setTabularFile] = useState<File | null>(null);
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<DatasetInspection | null>(null);
  const [datasetType, setDatasetType] = useState<UploadType>("events");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [inspecting, setInspecting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [documentUploading, setDocumentUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  async function loadDatasets() {
    setRefreshing(true);
    try {
      setDatasets(await getDatasets());
    } catch {
      setError("Could not load dataset history.");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { loadDatasets(); }, []);

  async function selectTabularFile(file?: File) {
    setError("");
    setMessage("");
    setInspection(null);
    setTabularFile(null);
    if (!file) return;
    const extension = file.name.toLowerCase().split(".").pop();
    if (!["csv", "xlsx"].includes(extension || "")) {
      setError("Please select a CSV or XLSX file.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError("Tabular files must not exceed 20 MB.");
      return;
    }
    setTabularFile(file);
    setInspecting(true);
    try {
      const result = await inspectDataset(file);
      setInspection(result);
      const detected = result.suggested_type || "events";
      setDatasetType(detected);
      setMapping(Object.fromEntries(
        Object.entries(result.mappings[detected]).map(([key, value]) => [key, value.column])
      ));
    } catch (err: any) {
      setTabularFile(null);
      setError(err.response?.data?.detail || "Could not inspect this file.");
    } finally {
      setInspecting(false);
    }
  }

  function changeType(type: UploadType) {
    setDatasetType(type);
    if (inspection) {
      setMapping(Object.fromEntries(
        Object.entries(inspection.mappings[type]).map(([key, value]) => [key, value.column])
      ));
    }
  }

  async function handleTabularUpload() {
    if (!tabularFile || !inspection) return;
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const result = await uploadDataset(datasetType, tabularFile, mapping);
      setMessage(`${result.data.filename} imported as ${datasetType}. ${result.data.rows.toLocaleString()} records validated and standardised.`);
      setTabularFile(null);
      setInspection(null);
      setMapping({});
      await loadDatasets();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Import failed. Check the selected column mapping.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDocumentUpload() {
    if (!documentFile) return;
    setDocumentUploading(true);
    setError("");
    setMessage("");
    try {
      const result = await uploadDocument(documentFile);
      setMessage(`${result.data.filename} uploaded. Text extraction completed (${result.data.rows.toLocaleString()} words).`);
      setDocumentFile(null);
      await loadDatasets();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Document upload failed.");
    } finally {
      setDocumentUploading(false);
    }
  }

  async function handlePreview(datasetId: string) {
    setError("");
    setMessage("");
    try {
      setPreview(await getDatasetPreview(datasetId));
    } catch {
      setError("Could not retrieve the dataset preview.");
    }
  }

  const mappingComplete = REQUIRED[datasetType].every(({ key }) => mapping[key]);

  return (
    <div className="upload-page">
      <div className="upload-heading">
        <div>
          <p className="upload-eyebrow">DATA MANAGEMENT</p>
          <h2>Data Sources</h2>
          <p>Import product data and documents. PulseOS inspects tabular files and helps map unfamiliar column names.</p>
        </div>
        <button className="refresh-button" onClick={loadDatasets} disabled={refreshing}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {message && <div className="upload-message success-message"><CheckCircle size={18} />{message}</div>}
      {error && <div className="upload-message error-message"><AlertCircle size={18} />{error}</div>}

      <div className="upload-cards">
        <div className="upload-card">
          <div className="upload-card-icon"><FileSpreadsheet size={23} /></div>
          <h3>CSV & Excel data</h3>
          <p>Import behavioural events, customer reviews, transactions or other supported tabular data.</p>
          <label className="file-picker">
            <UploadCloud size={19} /> Choose CSV or XLSX
            <input type="file" accept=".csv,.xlsx" onChange={(e) => selectTabularFile(e.target.files?.[0])} />
          </label>
          <div className="selected-file">{tabularFile?.name || "No file selected"}</div>
          {inspecting && <div className="processing-note"><Loader2 size={15} /> Inspecting columns and sample values…</div>}
          {inspection && (
            <div className="mapping-panel">
              <div className="mapping-heading">
                <strong>Map your columns</strong>
                <span>{inspection.row_count.toLocaleString()} rows detected</span>
              </div>
              <label className="mapping-field">
                Dataset purpose
                <select value={datasetType} onChange={(e) => changeType(e.target.value as UploadType)}>
                  <option value="events">Behavioural events</option>
                  <option value="reviews">Customer reviews</option>
                </select>
              </label>
              {REQUIRED[datasetType].map(({ key, label }) => (
                <label className="mapping-field" key={key}>
                  {label}
                  <select value={mapping[key] || ""} onChange={(e) => setMapping((old) => ({ ...old, [key]: e.target.value }))}>
                    <option value="">Select source column…</option>
                    {inspection.columns.map((column) => <option key={column} value={column}>{column}</option>)}
                  </select>
                  <small>
                    {inspection.mappings[datasetType][key]?.confidence >= 0.85
                      ? "High-confidence suggestion"
                      : mapping[key] ? "Please verify this mapping" : "No confident match found"}
                  </small>
                </label>
              ))}
              <div className="mapping-preview">
                <strong>Sample rows</strong>
                <div className="preview-table">
                  <table>
                    <thead><tr>{inspection.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                    <tbody>{inspection.preview.slice(0, 3).map((row, index) => (
                      <tr key={index}>{inspection.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
              <button className="upload-button" disabled={!mappingComplete || uploading} onClick={handleTabularUpload}>
                {uploading ? "Importing…" : "Validate & import dataset"} <ArrowRight size={15} />
              </button>
              <small>Required fields are standardised before analytics. Other columns are retained.</small>
            </div>
          )}
        </div>

        <div className="upload-card">
          <div className="upload-card-icon"><FileText size={23} /></div>
          <h3>PDF & Word documents</h3>
          <p>Upload product requirement documents, research reports, customer interview notes and strategy documents.</p>
          <label className="file-picker">
            <UploadCloud size={19} /> Choose PDF or DOCX
            <input type="file" accept=".pdf,.docx" onChange={(e) => {
              setError(""); setMessage("");
              const file = e.target.files?.[0];
              if (!file) return;
              if (file.size > 15 * 1024 * 1024) { setError("Documents must not exceed 15 MB."); return; }
              setDocumentFile(file);
            }} />
          </label>
          <div className="selected-file">{documentFile?.name || "No document selected"}</div>
          <button className="upload-button" disabled={!documentFile || documentUploading} onClick={handleDocumentUpload}>
            {documentUploading ? "Extracting text…" : "Upload document"}
          </button>
          <small>Text-based PDFs and DOCX are supported. Scanned PDF OCR is not enabled.</small>
        </div>
      </div>

      <section className="dataset-history">
        <div className="history-heading">
          <div><h3>Uploaded datasets & documents</h3><p>Files stored locally in this PulseOS instance</p></div>
          <span>{datasets.length} files</span>
        </div>
        {datasets.length === 0 ? <div className="history-empty">No files uploaded yet.</div> : (
          <div className="history-table">
            <div className="history-row history-header"><span>Filename</span><span>Type</span><span>Rows / words</span><span>Action</span></div>
            {datasets.map((dataset) => (
              <div className="history-row" key={dataset.id}>
                <span className="filename-cell">{dataset.dataset_type === "documents" ? <FileText size={17} /> : <FileSpreadsheet size={17} />}{dataset.original_filename}</span>
                <span>{dataset.dataset_type === "events" ? "Behaviour" : dataset.dataset_type === "reviews" ? "Reviews" : "Document"}</span>
                <span>{dataset.row_count.toLocaleString()}</span>
                <button className="preview-button" onClick={() => handlePreview(dataset.id)}><Eye size={15} /> Preview</button>
              </div>
            ))}
          </div>
        )}
      </section>

      {preview && (
        <section className="dataset-history preview-section">
          <div className="history-heading">
            <div><h3>{preview.filename}</h3><p>Showing a preview of the uploaded content</p></div>
            <button className="preview-button" onClick={() => setPreview(null)}>Close preview</button>
          </div>
          {preview.dataset_type === "documents" ? (
            <pre className="document-preview">{preview.extracted_text}</pre>
          ) : (
            <div className="preview-table">
              <table>
                <thead><tr>{Object.keys(preview.preview[0] || {}).map((key) => <th key={key}>{key}</th>)}</tr></thead>
                <tbody>{preview.preview.map((row: any, index: number) => (
                  <tr key={index}>{Object.keys(preview.preview[0] || {}).map((key) => <td key={key}>{String(row[key] ?? "")}</td>)}</tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default UploadData;
