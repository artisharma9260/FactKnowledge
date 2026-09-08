import { useEffect, useRef, useState } from "react";
import { CheckCircle, XCircle, Loader2, Clock } from "lucide-react";
import { documentsApi } from "@/lib/api";
import { POLL_INTERVAL_MS, STATUS_LABELS } from "@/constants";
import type { ProcessingStatus as ProcessingStatusType } from "@/types";

interface Props {
  documentId: number;
  initialStatus: string;
  onDone?: () => void;
}

export default function ProcessingStatus({ documentId, initialStatus, onDone }: Props) {
  const [status, setStatus] = useState<ProcessingStatusType | null>(null);
  const [polling, setPolling] = useState(
    initialStatus === "uploaded" || initialStatus === "processing"
  );
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = async () => {
    try {
      const s = await documentsApi.status(documentId);
      setStatus(s);
      if (s.status === "done" || s.status === "error") {
        setPolling(false);
        onDone?.();
      }
    } catch (err) {
      console.error("Status poll error:", err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [documentId]);

  useEffect(() => {
    if (!polling) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [polling, documentId]);

  const currentStatus = status?.status ?? initialStatus;

  const icon = {
    uploaded: <Clock className="w-4 h-4 text-muted-foreground" />,
    processing: <Loader2 className="w-4 h-4 text-primary animate-spin" />,
    done: <CheckCircle className="w-4 h-4 text-corroboration" />,
    error: <XCircle className="w-4 h-4 text-contradiction" />,
  }[currentStatus] ?? <Clock className="w-4 h-4 text-muted-foreground" />;

  const bgClass = {
    uploaded: "bg-secondary",
    processing: "bg-accent",
    done: "bg-corroboration-light border border-corroboration-border",
    error: "bg-contradiction-light border border-contradiction-border",
  }[currentStatus] ?? "bg-secondary";

  return (
    <div className={`rounded-lg p-4 ${bgClass}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="font-semibold text-sm">
          {STATUS_LABELS[currentStatus] ?? currentStatus}
        </span>
      </div>
      {status && (
        <>
          <p className="text-sm text-muted-foreground mb-2">{status.message}</p>
          {(status.facts_extracted > 0 || status.status === "done") && (
            <div className="flex gap-4 text-sm">
              <span>
                <strong className="text-foreground">{status.facts_extracted}</strong>{" "}
                <span className="text-muted-foreground">facts extracted</span>
              </span>
              <span>
                <strong className="text-foreground">{status.relationships_found}</strong>{" "}
                <span className="text-muted-foreground">relationships found</span>
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
