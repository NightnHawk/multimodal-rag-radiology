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
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Results</h2>
        {!result.quality_approved && (
          <button className="btn btn-secondary text-xs px-2.5 py-1" onClick={onRegenerate} disabled={loading}>
            {loading ? "Regenerating..." : "Regenerate"}
          </button>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            result.quality_approved ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          }`}
        >
          {result.quality_approved ? "Approved" : "Needs review"}
        </span>
        <span className="text-xs text-slate-600">Quality: {quality}%</span>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-slate-700 mb-1.5">Generated Description</h3>
        <p className="text-xs text-slate-800 whitespace-pre-line bg-slate-50 p-2.5 rounded leading-relaxed">
          {result.generated_description || "No description"}
        </p>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-slate-700 mb-1.5">Similar Reference Cases</h3>
        <div className="space-y-2">
          {result.retrieved_documents.map((doc, idx) => (
            <div key={idx} className="border border-slate-200 rounded p-2.5">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-semibold text-slate-900">Reference {idx + 1}</p>
                <span className="text-xs text-slate-500 font-mono">
                  {(doc.score ?? 0).toFixed(3)}
                </span>
              </div>
              <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                <span className="font-medium">Short:</span> {doc.short_description || "N/A"}
              </p>
              <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                <span className="font-medium">Full:</span> {doc.full_description || "N/A"}
              </p>
              <p className="text-xs text-slate-400 mt-1 break-all font-mono truncate">{doc.image_path}</p>
            </div>
          ))}
          {result.retrieved_documents.length === 0 && (
            <p className="text-xs text-slate-500">No retrieved documents.</p>
          )}
        </div>
      </div>
    </div>
  );
};






