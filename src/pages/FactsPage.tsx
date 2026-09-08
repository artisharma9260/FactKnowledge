import { useEffect, useState } from "react";
import {
  Search, ChevronLeft, ChevronRight, AlertTriangle, Database,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import FactCard from "@/components/features/FactCard";
import DocumentFilter from "@/components/features/DocumentFilter";
import { factsApi, documentsApi } from "@/lib/api";
import type { Document, Fact } from "@/types";

const PAGE_SIZE = 20;

export default function FactsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const fetchDocuments = async () => {
    try {
      const docs = await documentsApi.list();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  const fetchFacts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await factsApi.list({
        document_id: selectedDocId ?? undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setFacts(data);
    } catch (err) {
      console.error("Failed to load facts:", err);
      setError(err instanceof Error ? err.message : "Failed to load facts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    setPage(0);
  }, [selectedDocId, search]);

  useEffect(() => {
    fetchFacts();
  }, [selectedDocId, page]);

  const filteredFacts = search.trim()
    ? facts.filter(
        (f) =>
          f.claim.toLowerCase().includes(search.toLowerCase()) ||
          (f.entities ?? []).some((e) =>
            e.toLowerCase().includes(search.toLowerCase())
          )
      )
    : facts;

  return (
    <div className="page-container py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Extracted Facts</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Every factual claim extracted from uploaded documents, grounded in source evidence.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 max-w-sm">
          <DocumentFilter
            documents={documents}
            selectedDocId={selectedDocId}
            onSelect={setSelectedDocId}
          />
        </div>
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search claims or entities…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="
              w-full pl-9 pr-4 py-2 rounded-md border border-border bg-card
              text-sm text-foreground placeholder:text-muted-foreground
              focus:outline-none focus:ring-2 focus:ring-ring transition-colors
            "
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
        <div className="grid grid-cols-1 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card-base p-4 animate-pulse h-28 bg-secondary" />
          ))}
        </div>
      ) : filteredFacts.length === 0 ? (
        <div className="text-center py-16 card-base">
          <Database className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-base font-medium text-foreground">No facts found</p>
          <p className="text-sm text-muted-foreground mt-1">
            {selectedDocId ? "Try selecting a different document." : "Upload and process a PDF to get started."}
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {filteredFacts.length} fact{filteredFacts.length !== 1 ? "s" : ""}
            {search ? ` matching "${search}"` : ""}
          </p>
          <div className="grid grid-cols-1 gap-4">
            {filteredFacts.map((fact) => (
              <FactCard key={fact.id} fact={fact} />
            ))}
          </div>

          {/* Pagination */}
          {!search && (
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
                disabled={facts.length < PAGE_SIZE}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
