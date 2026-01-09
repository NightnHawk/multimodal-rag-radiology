import React, { useCallback, useMemo, useState } from "react";
import { UploadArea } from "./components/UploadArea";
import { Results } from "./components/Results";
import { History } from "./components/History";
import { queryImage, regenerate } from "./api";
import type { QueryResponse } from "./types";

type HistoryItem = {
  timestamp: number;
  fileName: string;
  result: QueryResponse;
  file?: File;
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [useRetrievedImages, setUseRetrievedImages] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const canAnalyze = useMemo(() => !!file && !loading, [file, loading]);

  const handleUpload = useCallback((f: File) => {
    setFile(f);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await queryImage(file, useRetrievedImages);
      setResult(res);
      setHistory((prev) => [...prev, { timestamp: Date.now(), fileName: file.name, result: res, file }]);
    } catch (err) {
      console.error(err);
      alert("Error processing the file. Check console for details.");
    } finally {
      setLoading(false);
    }
  }, [file, useRetrievedImages]);

  const handleRegenerate = useCallback(async () => {
    if (!result) return;
    setLoading(true);
    try {
      const res = await regenerate(result.query_id, file ?? undefined);
      setResult(res);
      setHistory((prev) => [...prev, { timestamp: Date.now(), fileName: file?.name ?? "Unknown", result: res, file }]);
    } catch (err) {
      console.error(err);
      alert("Error regenerating the answer. Check console for details.");
    } finally {
      setLoading(false);
    }
  }, [result, file]);

  const handleHistorySelect = useCallback((item: HistoryItem) => {
    setResult(item.result);
    setFile(item.file ?? null);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-slate-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">RAG RTG Search</h1>
            <p className="text-sm text-slate-500">DICOM / PNG / JPG retrieval + GPT-4o</p>
          </div>
          <div className="text-xs text-slate-500">
            API: {import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <UploadArea onFileSelected={handleUpload} />

            <div className="card p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <input
                  id="toggle"
                  type="checkbox"
                  className="h-4 w-4"
                  checked={useRetrievedImages}
                  onChange={(e) => setUseRetrievedImages(e.target.checked)}
                />
                <label htmlFor="toggle" className="text-sm text-slate-700">
                  Include retrieved images in GPT prompt
                </label>
              </div>
              <button
                className="btn btn-primary"
                disabled={!canAnalyze}
                onClick={handleAnalyze}
              >
                {loading ? "Processing..." : "Analyze"}
              </button>
            </div>

            <Results result={result} loading={loading} onRegenerate={handleRegenerate} />
          </div>

          <div className="space-y-4">
            <History items={history} onSelect={handleHistorySelect} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;





