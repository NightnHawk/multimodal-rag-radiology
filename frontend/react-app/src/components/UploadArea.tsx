import React, { useRef, useState } from "react";
import clsx from "clsx";

type Props = {
  onFileSelected: (file: File) => void;
};

export const UploadArea: React.FC<Props> = ({ onFileSelected }) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setSelectedName(file.name);
    onFileSelected(file);
  };

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-semibold">Upload Image</h2>
          <p className="text-sm text-slate-500">DICOM, PNG, or JPG</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          Browse
        </button>
      </div>

      <div
        className={clsx(
          "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
          dragOver ? "border-primary bg-indigo-50" : "border-slate-200 bg-slate-50"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragOver(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".dcm,.dicom,.png,.jpg,.jpeg"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <p className="text-sm text-slate-600">Click to upload or drag-and-drop</p>
        <p className="text-xs text-slate-500 mt-1">DICOM, PNG, JPG</p>
        {selectedName && (
          <p className="text-sm text-primary font-medium mt-3 break-all">
            Selected: {selectedName}
          </p>
        )}
      </div>
    </div>
  );
};





