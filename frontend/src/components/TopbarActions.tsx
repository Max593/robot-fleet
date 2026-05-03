import { Moon, RefreshCw, Sun } from "lucide-react";
import type { Theme } from "../types";

type TopbarActionsProps = {
  lastUpdatedAt: Date | null;
  theme: Theme;
  refreshLabel: string;
  onRefresh: () => void;
  onToggleTheme: () => void;
};

export function TopbarActions({ lastUpdatedAt, theme, refreshLabel, onRefresh, onToggleTheme }: TopbarActionsProps) {
  return (
    <div className="topbarActions">
      <span className="refreshTime">{lastUpdatedAt ? `Updated ${lastUpdatedAt.toLocaleTimeString()}` : "Waiting for data"}</span>
      <button
        className="iconButton"
        onClick={onToggleTheme}
        title={theme === "dark" ? "Use light mode" : "Use dark mode"}
        aria-label={theme === "dark" ? "Use light mode" : "Use dark mode"}
      >
        {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
      </button>
      <button className="iconButton" onClick={onRefresh} title={refreshLabel} aria-label={refreshLabel}>
        <RefreshCw size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
