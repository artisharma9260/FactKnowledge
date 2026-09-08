import { CheckCircle2, XCircle, Info, ArrowLeftRight, Sparkles } from "lucide-react";
import type { Relationship } from "@/types";
import FactCard from "./FactCard";
import { RELATIONSHIP_LABELS, RELATIONSHIP_DESCRIPTIONS } from "@/constants";

interface Props {
  relationship: Relationship;
}

const CATEGORY_CONFIG = {
  corroboration: {
    icon: CheckCircle2,
    badgeClass: "badge-corroboration",
    headerClass: "border-corroboration-border bg-corroboration-light",
    iconClass: "text-corroboration",
    dividerClass: "bg-corroboration/30",
  },
  contradiction: {
    icon: XCircle,
    badgeClass: "badge-contradiction",
    headerClass: "border-contradiction-border bg-contradiction-light",
    iconClass: "text-contradiction",
    dividerClass: "bg-contradiction/30",
  },
  context_explained: {
    icon: Info,
    badgeClass: "badge-context",
    headerClass: "border-context-border bg-context-light",
    iconClass: "text-context",
    dividerClass: "bg-context/30",
  },
} as const;

type Category = keyof typeof CATEGORY_CONFIG;

export default function RelationshipCard({ relationship }: Props) {
  const cat = relationship.category as Category;
  const config = CATEGORY_CONFIG[cat] ?? CATEGORY_CONFIG.corroboration;
  const { icon: Icon, badgeClass, headerClass, iconClass, dividerClass } = config;

  const scoreLabel =
    relationship.similarity_score !== null
      ? `${(relationship.similarity_score * 100).toFixed(1)}% similar`
      : null;

  return (
    <div className="card-base overflow-hidden">
      {/* Category header */}
      <div className={`flex items-center justify-between px-4 py-3 border-b ${headerClass}`}>
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${iconClass}`} />
          <span className={badgeClass}>{RELATIONSHIP_LABELS[cat] ?? cat}</span>
          <span className="text-xs text-muted-foreground hidden sm:inline">
            — {RELATIONSHIP_DESCRIPTIONS[cat]}
          </span>
        </div>
        {scoreLabel && (
          <span className="text-xs text-muted-foreground font-mono">{scoreLabel}</span>
        )}
      </div>

      {/* Facts side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-border">
        <div className="p-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Fact A
          </p>
          {relationship.fact_a ? (
            <FactCard fact={relationship.fact_a} compact />
          ) : (
            <p className="text-sm text-muted-foreground italic">Fact unavailable</p>
          )}
        </div>

        <div className="p-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <ArrowLeftRight className="w-3.5 h-3.5" />
            Fact B
          </p>
          {relationship.fact_b ? (
            <FactCard fact={relationship.fact_b} compact />
          ) : (
            <p className="text-sm text-muted-foreground italic">Fact unavailable</p>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div className="px-4 py-3 border-t border-border bg-muted/30">
        <div className="flex items-start gap-2">
          <Sparkles className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
              AI Reasoning
            </p>
            <p className="text-sm text-foreground leading-relaxed">{relationship.explanation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
