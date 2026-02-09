import React, { useRef, useState, useEffect } from "react";
import clsx from "clsx";
import { previewImage } from "../api";

type Props = {
  onFileSelected: (file: File) => void;
};

export const UploadArea: React.FC<Props> = ({ onFileSelected }) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDicom, setIsDicom] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setSelectedName(file.name);
    
    // Check if it's a DICOM file
    const isDicomFile = file.name.toLowerCase().endsWith('.dcm') || 
                        file.name.toLowerCase().endsWith('.dicom');
    setIsDicom(isDicomFile);
    
    // For regular images, create preview using FileReader
    if (!isDicomFile) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.onerror = () => {
        setPreviewUrl(null);
      };
      reader.readAsDataURL(file);
    } else {
      // For DICOM files, fetch preview from backend
      setLoadingPreview(true);
      setPreviewUrl(null);
      try {
        const preview = await previewImage(file);
        setPreviewUrl(preview);
      } catch (error) {
        console.error("Error loading DICOM preview:", error);
        setPreviewUrl(null);
      } finally {
        setLoadingPreview(false);
      }
    }
    
    onFileSelected(file);
  };

  // Cleanup preview URL when component unmounts or file changes
  useEffect(() => {
    return () => {
      if (previewUrl && !previewUrl.startsWith('data:')) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Upload Image</h2>
          <p className="text-xs text-slate-500 mt-0.5">DICOM, PNG, or JPG</p>
        </div>
        <button
          className="btn btn-secondary text-xs px-3 py-1.5"
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          Browse
        </button>
      </div>

      <div
        className={clsx(
          "border-2 border-dashed rounded-lg transition-colors",
          dragOver ? "border-primary bg-indigo-50" : "border-slate-200 bg-slate-50",
          previewUrl || isDicom || loadingPreview ? "p-3" : "p-6 text-center"
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
        onClick={() => !previewUrl && !isDicom && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".dcm,.dicom,.png,.jpg,.jpeg"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        
        {loadingPreview ? (
          <div className="space-y-2">
            <div className="relative w-full rounded overflow-hidden bg-slate-100 border border-slate-200 p-8 flex flex-col items-center justify-center min-h-[160px]">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-2"></div>
              <p className="text-xs font-medium text-slate-700">Loading DICOM preview...</p>
              <p className="text-xs text-slate-500 mt-1 truncate max-w-full">{selectedName}</p>
            </div>
          </div>
        ) : previewUrl ? (
          <div className="space-y-2">
            <div className="relative w-full rounded overflow-hidden bg-slate-100 border border-slate-200">
              <img
                src={previewUrl}
                alt="Preview"
                className="w-full h-auto max-h-64 object-contain mx-auto"
              />
            </div>
            <div className="text-center">
              <p className="text-xs text-primary font-medium break-all px-1">
                {selectedName}
              </p>
              <button
                className="text-xs text-slate-500 hover:text-slate-700 mt-0.5 underline"
                onClick={(e) => {
                  e.stopPropagation();
                  inputRef.current?.click();
                }}
                type="button"
              >
                Change file
              </button>
            </div>
          </div>
        ) : isDicom ? (
          <div className="space-y-2">
            <div className="relative w-full rounded overflow-hidden bg-slate-100 border border-slate-200 p-8 flex flex-col items-center justify-center min-h-[160px]">
              <svg
                className="w-12 h-12 text-slate-400 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-xs font-medium text-slate-700">DICOM File</p>
              <p className="text-xs text-slate-500 mt-0.5 truncate max-w-full">{selectedName}</p>
              <p className="text-xs text-red-500 mt-1">Preview unavailable</p>
            </div>
            <div className="text-center">
              <button
                className="text-xs text-slate-500 hover:text-slate-700 underline"
                onClick={(e) => {
                  e.stopPropagation();
                  inputRef.current?.click();
                }}
                type="button"
              >
                Change file
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-600">Click to upload or drag-and-drop</p>
            <p className="text-xs text-slate-500 mt-0.5">DICOM, PNG, JPG</p>
            {selectedName && (
              <p className="text-xs text-primary font-medium mt-2 break-all">
                Selected: {selectedName}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
};






