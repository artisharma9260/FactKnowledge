import { useEffect, useState } from "react";
import {
  CheckCircle2, XCircle, Info, GitCompare, AlertTriangle, ChevronLeft, ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import RelationshipCard from "@/components/features/RelationshipCard";
import DocumentFilter from "@/components/features/DocumentFilter";
import { relationshipsApi, documentsApi } from "@/lib/api";
import { RELATIONSHIP_LABELS, RELATIONSHIP_DESCRIPTIONS } from "@/constants";
import type { Document, Relationship, RelationshipCategory } from "@/types";

const PAGE_SIZE = 20;

const CATEGORY_TABS: { key: RelationshipCategory | null; label: string; icon: React.ElementType; badgeClass: string }[] = [
  { key: null, label: "All", icon: GitCompare, badgeClass: "bg-secondary text-secondary-foreground border border-border" },
  { key: "corroboration", label: "Corroboration", icon: CheckCircle2, badgeClass: "badge-corroboration" },
  { key: "contradiction", label: "Contradiction", icon: XCircle, badgeClass: "badge-contradiction" },
  { key: "context_explained", label: "Context-Explained", icon: Info, badgeClass: "badge-context" },
];

export default function RelationshipsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedCategory, setSelectedCategory] = useState<RelationshipCategory | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [page, setPage] = useState(0);

  // Summary counts
  const [counts, setCounts] = useState<Record<string, number>>({});

  const fetchDocuments = async () => {
    try {
      const docs = await documentsApi.list();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  const fetchCounts = async () => {
    try {
      const [all, corr, cont, ctx] = await Promise.all([
        relationshipsApi.list({ limit: 1 }),
        relationshipsApi.list({ category: "corroboration", limit: 500 }),
        relationshipsApi.list({ category: "contradiction", limit: 500 }),
        relationshipsApi.list({ category: "context_explained", limit: 500 }),
      ]);
      setCounts({
        corroboration: corr.length,
        contradiction: cont.length,
        context_explained: ctx.length,
      });
    } catch {
      // ignore count errors
    }
  };

  const fetchRelationships = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await relationshipsApi.list({
        category: selectedCategory ?? undefined,
        document_id: selectedDocId ?? undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setRelationships(data);
    } catch (err) {
      console.error("Failed to load relationships:", err);
      setError(err instanceof Error ? err.message : "Failed to load relationships.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDocuments(); fetchCounts(); }, []);

  useEffect(() => { setPage(0); }, [selectedCategory, selectedDocId]);

  useEffect(() => { fetchRelationships(); }, [selectedCategory, selectedDocId, page]);

  return (
    <div className="page-container py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Cross-Document Relationships</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Facts detected as related across documents, classified by Gemini into corroboration,
          contradiction, or context-explained.
        </p>
      </div>

      {/* Summary cards */}
      {Object.keys(counts).length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { key: "corroboration", label: "Corroborations", icon: CheckCircle2, cls: "text-corroboration" },
            { key: "contradiction", label: "Contradictions", icon: XCircle, cls: "text-contradiction" },
            { key: "context_explained", label: "Context-Explained", icon: Info, cls: "text-context" },
          ].map(({ key, label, icon: Icon, cls }) => (
            <button
              key={key}
              onClick={() =>
                setSelectedCategory((prev) =>
                  prev === key ? null : (key as RelationshipCategory)
                )
              }
              className={`
                card-base p-4 text-left transition-all hover:shadow-md
                ${selectedCategory === key ? "ring-2 ring-primary" : ""}
              `}
            >
              <Icon className={`w-5 h-5 mb-2 ${cls}`} />
              <p className="text-2xl font-bold text-foreground">{counts[key] ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Category tabs */}
        <div className="flex gap-1 flex-wrap">
          {CATEGORY_TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={String(key)}
              onClick={() => setSelectedCategory(key)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors
                ${selectedCategory === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        <div className="sm:ml-auto max-w-xs w-full">
          <DocumentFilter
            documents={documents}
            selectedDocId={selectedDocId}
            onSelect={setSelectedDocId}
          />
        </div>
      </div>

      {/* Content */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-contradiction-light border border-contradiction-border text-contradiction-text text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card-base animate-pulse h-48 bg-secondary" />
          ))}
        </div>
      ) : relationships.length === 0 ? (
        <div className="text-center py-16 card-base">
          <GitCompare className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-base font-medium text-foreground">No relationships found</p>
          <p className="text-sm text-muted-foreground mt-1">
            {selectedCategory
              ? `No ${RELATIONSHIP_LABELS[selectedCategory]} relationships detected.`
              : "Upload at least two documents to detect cross-document relationships."}
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {relationships.length} relationship{relationships.length !== 1 ? "s" : ""}
            {selectedCategory ? ` · ${RELATIONSHIP_LABELS[selectedCategory]}` : ""}
          </p>
          <div className="space-y-4">
            {relationships.map((rel) => (
              <RelationshipCard key={rel.id} relationship={rel} />
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">Page {page + 1}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={relationships.length < PAGE_SIZE}
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
