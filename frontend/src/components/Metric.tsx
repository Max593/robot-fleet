import type { ReactNode } from "react";

type MetricProps = {
  label: string;
  value: number;
  tone: "blue" | "green" | "red" | "amber" | "slate" | "purple" | "cyan";
  icon: ReactNode;
  isActive: boolean;
  onClick: () => void;
};

export function Metric({ label, value, tone, icon, isActive, onClick }: MetricProps) {
  return (
    <button
      className={`metric metric-${tone}${isActive ? " metric-active" : ""}`}
      onClick={onClick}
      type="button"
      aria-pressed={isActive}
    >
      <div className="metricIcon" aria-hidden="true">
        {icon}
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </button>
  );
}
