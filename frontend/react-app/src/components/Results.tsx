import React from "react";
import type { QueryResponse } from "../types";

type Props = {
  result: QueryResponse | null;
  loading: boolean;
  onRegenerate: () => void;
};

export const Results: React.FC<Props> = ({ result, loading, onRegenerate }) => {
  if (!result) return null;

  const quality = result.quality_score !== null ? (result.quality_score * 100).toFixed(1) : "N/A";

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Results</h2>
        {!result.quality_approved && (
          <button className="btn btn-secondary" onClick={onRegenerate} disabled={loading}>
            {loading ? "Regenerating..." : "Regenerate"}
          </button>
        )}
      </div>

      <div className="flex items-center gap-3">
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold ${
            result.quality_approved ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          }`}
        >
          {result.quality_approved ? "Approved" : "Needs review"}
        </span>
        <span className="text-sm text-slate-600">Quality score: {quality}</span>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Generated Description</h3>
        <p className="text-sm text-slate-800 whitespace-pre-line bg-slate-50 p-3 rounded">
          {result.generated_description || "No description"}
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Similar Reference Cases</h3>
        <div className="space-y-3">
          {result.retrieved_documents.map((doc, idx) => (
            <div key={idx} className="border border-slate-200 rounded p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">Reference {idx + 1}</p>
                <span className="text-xs text-slate-500">
                  Score: {doc.score?.toFixed(4) ?? "N/A"}
                </span>
              </div>
              <p className="text-sm text-slate-700 mt-1">
                <strong>Short:</strong> {doc.short_description || "N/A"}
              </p>
              <p className="text-sm text-slate-700 mt-1">
                <strong>Full:</strong> {doc.full_description || "N/A"}
              </p>
              <p className="text-xs text-slate-500 mt-1 break-all">{doc.image_path}</p>
            </div>
          ))}
          {result.retrieved_documents.length === 0 && (
            <p className="text-sm text-slate-500">No retrieved documents.</p>
          )}
        </div>
      </div>
    </div>
  );
};





