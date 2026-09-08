import { FileText, Calendar, Hash, Building2, Quote } from "lucide-react";
import type { Fact } from "@/types";

interface Props {
  fact: Fact;
  compact?: boolean;
}

export default function FactCard({ fact, compact = false }: Props) {
  const docName = fact.document_original_name ?? `Doc #${fact.document_id}`;

  return (
    <div className="card-base p-4 space-y-3">
      {/* Claim */}
      <p className={`font-medium text-foreground leading-snug ${compact ? "text-sm" : "text-base"}`}>
        {fact.claim}
      </p>

      {/* Meta row */}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <FileText className="w-3.5 h-3.5" />
          <span className="font-medium text-foreground/80 truncate max-w-[200px]">{docName}</span>
        </span>
        {fact.page_number !== null && (
          <span className="flex items-center gap-1">
            <Hash className="w-3.5 h-3.5" />
            Page {fact.page_number}
          </span>
        )}
        {fact.time_period && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {fact.time_period}
          </span>
        )}
      </div>

      {/* Entities */}
      {fact.entities && fact.entities.length > 0 && (
        <div className="flex items-start gap-1.5 flex-wrap">
          <Building2 className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
          {fact.entities.map((e) => (
            <span
              key={e}
              className="px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground text-xs font-medium"
            >
              {e}
            </span>
          ))}
        </div>
      )}

      {/* Numbers */}
      {fact.numbers && fact.numbers.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {fact.numbers.map((n, i) => (
            <span
              key={i}
              className="px-2 py-0.5 rounded-md bg-accent text-accent-foreground text-xs font-mono font-medium"
            >
              {n.value !== null ? `${n.value}` : "—"}
              {n.unit ? ` ${n.unit}` : ""}
              {n.context ? ` · ${n.context}` : ""}
            </span>
          ))}
        </div>
      )}

      {/* Source quote */}
      {!compact && fact.source_quote && (
        <blockquote className="source-quote">
          <Quote className="w-3 h-3 inline mr-1 text-primary/50" />
          {fact.source_quote}
        </blockquote>
      )}
    </div>
  );
}
