import { Battery } from "lucide-react";

export function BatteryCell({ level }: { level: number | null }) {
  if (level === null) {
    return <span className="muted">unknown</span>;
  }

  const batteryClass = level < 20 ? "batteryLow" : level < 50 ? "batteryMid" : "batteryHigh";
  return (
    <span className="batteryCell">
      <Battery size={15} aria-hidden="true" />
      <span className={`batteryBar ${batteryClass}`}>
        <span style={{ width: `${level}%` }} />
      </span>
      <span>{level}%</span>
    </span>
  );
}
