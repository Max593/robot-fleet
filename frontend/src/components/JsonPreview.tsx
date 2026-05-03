import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { formatJson } from "../utils/format";

type JsonPreviewProps = {
  value: Record<string, unknown> | string | null;
  emptyLabel?: string;
};

export function JsonPreview({ value, emptyLabel = "none" }: JsonPreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (value === null) {
    return <span className="muted">{emptyLabel}</span>;
  }

  const previewText = typeof value === "string" ? value : formatJson(value);
  const expandedText = typeof value === "string" ? value : JSON.stringify(value, null, 2);

  return (
    <div className="jsonPreview">
      <button className="jsonPreviewToggle" type="button" onClick={() => setIsExpanded((current) => !current)}>
        {isExpanded ? <ChevronDown size={15} aria-hidden="true" /> : <ChevronRight size={15} aria-hidden="true" />}
        <code className="jsonPayload">{previewText}</code>
      </button>
      {isExpanded ? <pre className="jsonExpanded">{expandedText}</pre> : null}
    </div>
  );
}
