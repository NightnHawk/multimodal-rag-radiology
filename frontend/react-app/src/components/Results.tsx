import React from "react";
import type { QueryResponse } from "../types";

type Props = {
  result: QueryResponse | null;
  loading: boolean;
  onRegenerate: () => void;
};

export const Results: React.FC<Props> = ({ result, loading, onRegenerate }) => {
  if (!result) return null;

  // Defensive checks for result structure
  const quality = result.quality_score !== null && result.quality_score !== undefined 
    ? (result.quality_score * 100).toFixed(1) 
    : "N/A";
  
  const retrievedDocs = result.retrieved_documents || [];
  const validationInfo = result.validation_info;

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
        {validationInfo && (
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              validationInfo.passed_validation
                ? "bg-blue-100 text-blue-700"
                : "bg-orange-100 text-orange-700"
            }`}
            title={`Validation: ${validationInfo.validated_count || 0}/${validationInfo.total_documents || 0} documents passed`}
          >
            {validationInfo.passed_validation ? "✓ Validated" : "⚠ Low similarity"}
          </span>
        )}
      </div>
      
      {validationInfo && (
        <div className="bg-slate-50 p-2 rounded text-xs">
          <p className="text-slate-700 font-medium mb-1">Description Validation</p>
          <div className="flex items-center gap-3 text-slate-600">
            <span>
              {validationInfo.validated_count || 0}/{validationInfo.total_documents || 0} validated
            </span>
            <span>•</span>
            <span>
              Ratio: {((validationInfo.approval_ratio || 0) * 100).toFixed(0)}%
            </span>
            {(validationInfo.outlier_count || 0) > 0 && (
              <>
                <span>•</span>
                <span className="text-orange-600">
                  {validationInfo.outlier_count} outlier{(validationInfo.outlier_count || 0) > 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-xs font-semibold text-slate-700 mb-1.5">Generated Description</h3>
        <p className="text-xs text-slate-800 whitespace-pre-line bg-slate-50 p-2.5 rounded leading-relaxed">
          {result.generated_description || "No description"}
        </p>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-slate-700 mb-1.5">Similar Reference Cases</h3>
        <div className="space-y-2">
          {retrievedDocs.length > 0 ? (
            retrievedDocs.map((doc, idx) => (
              <div key={idx} className="border border-slate-200 rounded p-2.5">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs font-semibold text-slate-900">Reference {idx + 1}</p>
                  <div className="flex items-center gap-2">
                    {doc.mean_similarity !== undefined && doc.mean_similarity !== null && (
                      <span
                        className={`text-xs font-mono ${
                          doc.mean_similarity >= 0.5
                            ? "text-blue-600"
                            : "text-orange-600"
                        }`}
                        title="Mean similarity to other retrieved documents"
                      >
                        Sim: {Number(doc.mean_similarity).toFixed(2)}
                      </span>
                    )}
                    <span className="text-xs text-slate-500 font-mono">
                      Score: {((doc.score ?? 0) as number).toFixed(3)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                  <span className="font-medium">Short:</span> {doc.short_description || "N/A"}
                </p>
                <p className="text-xs text-slate-700 mt-0.5 leading-relaxed">
                  <span className="font-medium">Full:</span> {doc.full_description || "N/A"}
                </p>
                <p className="text-xs text-slate-400 mt-1 break-all font-mono truncate">{doc.image_path || "N/A"}</p>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">No retrieved documents.</p>
          )}
        </div>
      </div>
    </div>
  );
};






