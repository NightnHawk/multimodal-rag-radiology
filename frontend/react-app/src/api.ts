import axios from "axios";
import type { QueryResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" }
});

export async function queryImage(file: File, useRetrievedImages: boolean): Promise<QueryResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("use_retrieved_images", String(useRetrievedImages));

  const { data } = await api.post<QueryResponse>("/query", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function regenerate(queryId: string, file?: File): Promise<QueryResponse> {
  const form = new FormData();
  form.append("query_id", queryId);
  form.append("use_same_retrieval", "false");
  if (file) form.append("file", file);

  const { data } = await api.post<QueryResponse>("/query/regenerate", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}





