
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export async function getHealth() {
  const response = await api.get("/api/health");
  return response.data;
}

export async function uploadDataset(
  datasetType: "events" | "reviews",
  file: File
) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    `/api/datasets/upload/${datasetType}`,
    formData
  );

  return response.data;
}

export async function getDatasets() {
  const response = await api.get("/api/datasets");
  return response.data.datasets;
}

export async function getDatasetPreview(datasetId: string) {
  const response = await api.get(
    `/api/datasets/${datasetId}/preview`
  );

  return response.data;
}

