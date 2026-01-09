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
    <div className="card p-6 space-y-3">
      <h2 className="text-lg font-semibold">History</h2>
      <div className="divide-y divide-slate-200">
        {items
          .slice()
          .reverse()
          .map((item, idx) => (
            <button
              key={idx}
              className="w-full text-left py-3 hover:bg-slate-50 transition-colors"
              onClick={() => onSelect(item)}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-800">{item.fileName}</span>
                <span className="text-xs text-slate-500">
                  {new Date(item.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-xs text-slate-500 truncate">
                {item.result.generated_description?.slice(0, 120) || "No description"}
              </p>
            </button>
          ))}
      </div>
    </div>
  );
};





