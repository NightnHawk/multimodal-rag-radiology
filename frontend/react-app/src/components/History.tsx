import React from "react";
import type { QueryResponse } from "../types";

type HistoryItem = {
  timestamp: number;
  fileName: string;
  result: QueryResponse;
};

type Props = {
  items: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
};

export const History: React.FC<Props> = ({ items, onSelect }) => {
  if (items.length === 0) return null;

  return (
    <div className="card p-4">
      <h2 className="text-sm font-semibold text-slate-900 mb-2.5">History</h2>
      <div className="divide-y divide-slate-200 max-h-[calc(100vh-12rem)] overflow-y-auto">
        {items
          .slice()
          .reverse()
          .map((item, idx) => (
            <button
              key={idx}
              className="w-full text-left py-2 px-1 hover:bg-slate-50 transition-colors rounded"
              onClick={() => onSelect(item)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-slate-800 truncate mr-2">{item.fileName}</span>
                <span className="text-xs text-slate-400 flex-shrink-0">
                  {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed truncate">
                {item.result.generated_description?.slice(0, 100) || "No description"}
              </p>
            </button>
          ))}
      </div>
    </div>
  );
};






