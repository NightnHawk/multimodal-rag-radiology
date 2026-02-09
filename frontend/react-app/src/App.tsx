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
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-2.5 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">RAG RTG Search</h1>
            <p className="text-xs text-slate-500 mt-0.5">DICOM / PNG / JPG retrieval + GPT-4o</p>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            {import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="lg:col-span-2 space-y-3">
            <UploadArea onFileSelected={handleUpload} />

            <div className="card p-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <input
                  id="toggle"
                  type="checkbox"
                  className="h-3.5 w-3.5 rounded border-slate-300 text-primary focus:ring-primary"
                  checked={useRetrievedImages}
                  onChange={(e) => setUseRetrievedImages(e.target.checked)}
                />
                <label htmlFor="toggle" className="text-xs text-slate-700 cursor-pointer">
                  Include retrieved images in GPT prompt
                </label>
              </div>
              <button
                className="btn btn-primary text-sm px-3 py-1.5"
                disabled={!canAnalyze}
                onClick={handleAnalyze}
              >
                {loading ? "Processing..." : "Analyze"}
              </button>
            </div>

            <Results result={result} loading={loading} onRegenerate={handleRegenerate} />
          </div>

          <div>
            <History items={history} onSelect={handleHistorySelect} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;






