import { FileText, ChevronDown } from "lucide-react";
import type { Document } from "@/types";

interface Props {
  documents: Document[];
  selectedDocId: number | null;
  onSelect: (id: number | null) => void;
}

export default function DocumentFilter({ documents, selectedDocId, onSelect }: Props) {
  return (
    <div className="relative">
      <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
      <select
        value={selectedDocId ?? ""}
        onChange={(e) => onSelect(e.target.value ? Number(e.target.value) : null)}
        className="
          appearance-none w-full pl-9 pr-8 py-2 rounded-md border border-border bg-card
          text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring
          transition-colors hover:border-primary/50
        "
      >
        <option value="">All Documents</option>
        {documents
          .filter((d) => d.status === "done")
          .map((d) => (
            <option key={d.id} value={d.id}>
              {d.original_name}
            </option>
          ))}
      </select>
      <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
    </div>
  );
}
