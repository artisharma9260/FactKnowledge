import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Trash2, FileText, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import DocumentUploader from "@/components/features/DocumentUploader";
import ProcessingStatus from "@/components/features/ProcessingStatus";
import { documentsApi } from "@/lib/api";
import { STATUS_LABELS } from "@/constants";
import type { Document } from "@/types";

export default function UploadPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      const docs = await documentsApi.list();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleUploaded = (doc: Document) => {
    setDocuments((prev) => [doc, ...prev]);
  };

  const handleDelete = async (id: number) => {
    setDeleteError(null);
    try {
      await documentsApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed.");
    }
  };

  const statusColor: Record<string, string> = {
    uploaded: "text-muted-foreground",
    processing: "text-primary",
    done: "text-corroboration-text",
    error: "text-contradiction-text",
  };

  return (
    <div className="page-container py-8 space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Document Upload</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Upload PDF documents to extract facts and detect cross-document relationships.
          Each document is processed incrementally — existing documents are never re-extracted.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Upload panel */}
        <div className="lg:col-span-3 space-y-6">
          <div className="card-base p-6">
            <h2 className="text-base font-semibold mb-4">Upload New Document</h2>
            <DocumentUploader onUploaded={handleUploaded} />
          </div>

          {/* Pipeline description */}
          <div className="card-base p-5 space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Processing Pipeline</h3>
            <ol className="space-y-2 text-sm text-muted-foreground list-none">
              {[
                ["1", "PDF parsed page-by-page, preserving page numbers and table data"],
                ["2", "Each page sent to Gemini for structured fact extraction"],
                ["3", "Facts embedded with text-embedding-004 for semantic search"],
                ["4", "New facts compared against all existing facts using cosine similarity"],
                ["5", "Candidate pairs classified by Gemini as corroboration / contradiction / context-explained"],
              ].map(([n, desc]) => (
                <li key={n} className="flex gap-3">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                    {n}
                  </span>
                  <span>{desc}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Documents list */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">
              Documents ({documents.length})
            </h2>
            {documents.some((d) => d.status === "done") && (
              <Link to="/facts">
                <Button variant="ghost" size="sm" className="gap-1 text-primary">
                  View Facts <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            )}
          </div>

          {deleteError && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-contradiction-light border border-contradiction-border text-contradiction-text text-sm">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {deleteError}
            </div>
          )}

          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : documents.length === 0 ? (
            <div className="card-base p-6 text-center">
              <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No documents yet.</p>
              <p className="text-xs text-muted-foreground mt-1">Upload your first PDF above.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div key={doc.id} className="card-base p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate text-foreground">
                        {doc.original_name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs font-medium ${statusColor[doc.status] ?? "text-muted-foreground"}`}>
                          {STATUS_LABELS[doc.status] ?? doc.status}
                        </span>
                        {doc.page_count && (
                          <span className="text-xs text-muted-foreground">
                            · {doc.page_count} pages
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-1.5 rounded hover:bg-contradiction-light transition-colors flex-shrink-0"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4 text-muted-foreground hover:text-contradiction" />
                    </button>
                  </div>

                  {(doc.status === "processing" || doc.status === "uploaded" || doc.status === "done" || doc.status === "error") && (
                    <ProcessingStatus
                      documentId={doc.id}
                      initialStatus={doc.status}
                      onDone={fetchDocuments}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
