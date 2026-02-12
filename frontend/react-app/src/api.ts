import axios, { AxiosError } from "axios";
import type { QueryResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" }
});

export async function queryImage(
  file: File, 
  useRetrievedImages: boolean, 
  clearContext: boolean = false
): Promise<QueryResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("use_retrieved_images", String(useRetrievedImages));
  form.append("clear_context", String(clearContext));

  try {
    const { data } = await api.post<QueryResponse>("/query", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    console.log("API Response received:", data);
    return data;
  } catch (error) {
    console.error("API Error:", error);
    if (axios.isAxiosError(error)) {
      console.error("Response data:", error.response?.data);
      console.error("Response status:", error.response?.status);
    }
    throw error;
  }
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

export async function previewImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post<{ image: string; format: string }>("/preview", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data.image;
}






