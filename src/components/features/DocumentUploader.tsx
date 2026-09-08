import { useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { documentsApi } from "@/lib/api";
import type { Document } from "@/types";

interface Props {
  onUploaded: (doc: Document) => void;
}

export default function DocumentUploader({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    setError(null);
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const doc = await documentsApi.upload(selectedFile);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded(doc);
    } catch (err) {
      console.error("Upload error:", err);
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-10 cursor-pointer
          flex flex-col items-center justify-center gap-3 transition-colors
          ${dragging
            ? "border-primary bg-accent"
            : "border-border hover:border-primary/50 hover:bg-secondary/50"
          }
        `}
      >
        <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center">
          <Upload className="w-6 h-6 text-primary" />
        </div>
        <div className="text-center">
          <p className="font-semibold text-foreground">Drop a PDF here</p>
          <p className="text-sm text-muted-foreground mt-0.5">
            or click to browse — supports 25–100 page corporate filings and reports
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="sr-only"
          onChange={handleInputChange}
        />
      </div>

      {/* Selected file */}
      {selectedFile && (
        <div className="flex items-center justify-between card-base px-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <FileText className="w-5 h-5 text-primary flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>
          <button
            onClick={() => { setSelectedFile(null); setError(null); }}
            className="ml-3 p-1 rounded hover:bg-secondary transition-colors"
            aria-label="Remove file"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-sm text-contradiction font-medium">{error}</p>
      )}

      {/* Upload button */}
      <Button
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        className="w-full"
        size="lg"
      >
        {uploading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Uploading…
          </span>
        ) : (
          "Upload & Process"
        )}
      </Button>
    </div>
  );
}
