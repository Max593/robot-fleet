import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Activity, Battery, ChevronLeft, ChevronRight, CirclePause, CirclePlay, RefreshCw, Search, Wifi, WifiOff } from "lucide-react";

type Robot = {
  robot_id: string;
  status: "idle" | "running";
  battery_level: number | null;
  last_seen_at: string | null;
  last_seen_seconds_ago: number | null;
  is_online: boolean;
};

type RobotsResponse = {
  robots: Robot[];
};

type StatusFilter = "all" | "online" | "offline" | "running" | "idle";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const pageSize = 25;

function App() {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);

  const loadRobots = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${apiBaseUrl}/robots/status`);
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      const data = (await response.json()) as RobotsResponse;
      setRobots(data.robots);
      setLastUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load robot status");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRobots();
    const intervalId = window.setInterval(() => void loadRobots(), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadRobots]);

  const summary = useMemo(() => {
    const online = robots.filter((robot) => robot.is_online).length;
    const running = robots.filter((robot) => robot.is_online && robot.status === "running").length;
    const idle = robots.filter((robot) => robot.is_online && robot.status === "idle").length;
    return {
      total: robots.length,
      online,
      offline: robots.length - online,
      running,
      idle
    };
  }, [robots]);

  const filteredRobots = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    return robots.filter((robot) => {
      const matchesSearch = normalizedSearch.length === 0 || robot.robot_id.toLowerCase().includes(normalizedSearch);
      return matchesSearch && matchesStatusFilter(robot, statusFilter);
    });
  }, [robots, searchTerm, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRobots.length / pageSize));
  const pageStart = (currentPage - 1) * pageSize;
  const pageEnd = pageStart + pageSize;
  const visibleRobots = filteredRobots.slice(pageStart, pageEnd);
  const firstVisibleRow = filteredRobots.length === 0 ? 0 : pageStart + 1;
  const lastVisibleRow = Math.min(pageEnd, filteredRobots.length);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, statusFilter]);

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, totalPages));
  }, [totalPages]);

  return (
    <main className="shell">
      <section className="topbar" aria-label="Fleet overview">
        <div>
          <p className="eyebrow">Local Robot Fleet</p>
          <h1>Operations Dashboard</h1>
        </div>
        <div className="topbarActions">
          <span className="refreshTime">{lastUpdatedAt ? `Updated ${lastUpdatedAt.toLocaleTimeString()}` : "Waiting for data"}</span>
          <button className="iconButton" onClick={() => void loadRobots()} title="Refresh fleet status" aria-label="Refresh fleet status">
            <RefreshCw size={18} aria-hidden="true" />
          </button>
        </div>
      </section>

      <section className="metrics" aria-label="Fleet metrics">
        <Metric
          label="Total"
          value={summary.total}
          tone="blue"
          icon={<Activity size={18} />}
          isActive={statusFilter === "all"}
          onClick={() => setStatusFilter("all")}
        />
        <Metric
          label="Online"
          value={summary.online}
          tone="green"
          icon={<Wifi size={18} />}
          isActive={statusFilter === "online"}
          onClick={() => setStatusFilter((filter) => (filter === "online" ? "all" : "online"))}
        />
        <Metric
          label="Offline"
          value={summary.offline}
          tone="red"
          icon={<WifiOff size={18} />}
          isActive={statusFilter === "offline"}
          onClick={() => setStatusFilter((filter) => (filter === "offline" ? "all" : "offline"))}
        />
        <Metric
          label="Running"
          value={summary.running}
          tone="amber"
          icon={<CirclePlay size={18} />}
          isActive={statusFilter === "running"}
          onClick={() => setStatusFilter((filter) => (filter === "running" ? "all" : "running"))}
        />
        <Metric
          label="Idle"
          value={summary.idle}
          tone="slate"
          icon={<CirclePause size={18} />}
          isActive={statusFilter === "idle"}
          onClick={() => setStatusFilter((filter) => (filter === "idle" ? "all" : "idle"))}
        />
      </section>

      {error ? <div className="notice error">{error}</div> : null}

      <section className="tableSection" aria-label="Robot status table">
        <div className="sectionHeader">
          <h2>Robots</h2>
          <span>{isLoading ? "Loading" : `${filteredRobots.length} shown of ${robots.length} tracked`}</span>
        </div>

        <div className="tableTools">
          <label className="searchBox">
            <Search size={16} aria-hidden="true" />
            <span className="srOnly">Search robots</span>
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search robot ID"
              type="search"
            />
          </label>
        </div>

        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Robot</th>
                <th>Connectivity</th>
                <th>Status</th>
                <th>Battery</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {visibleRobots.map((robot) => (
                <tr key={robot.robot_id}>
                  <td className="robotId">{robot.robot_id}</td>
                  <td>
                    <StatusPill online={robot.is_online} />
                  </td>
                  <td>
                    <span className={`state state-${robot.status}`}>{robot.status}</span>
                  </td>
                  <td>
                    <BatteryCell level={robot.battery_level} />
                  </td>
                  <td>{formatLastSeen(robot.last_seen_seconds_ago)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && robots.length === 0 ? <div className="emptyState">No robots have checked in yet.</div> : null}
          {!isLoading && robots.length > 0 && filteredRobots.length === 0 ? <div className="emptyState">No robots match the current filters.</div> : null}
        </div>

        <div className="paginationBar" aria-label="Robot table pagination">
          <span>
            Rows {firstVisibleRow}-{lastVisibleRow} of {filteredRobots.length}
          </span>
          <div className="paginationControls">
            <button
              className="pageButton"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={currentPage <= 1}
              title="Previous page"
              aria-label="Previous page"
            >
              <ChevronLeft size={17} aria-hidden="true" />
            </button>
            <span className="pageCount">
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="pageButton"
              onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
              disabled={currentPage >= totalPages}
              title="Next page"
              aria-label="Next page"
            >
              <ChevronRight size={17} aria-hidden="true" />
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

type MetricProps = {
  label: string;
  value: number;
  tone: "blue" | "green" | "red" | "amber" | "slate";
  icon: ReactNode;
  isActive: boolean;
  onClick: () => void;
};

function Metric({ label, value, tone, icon, isActive, onClick }: MetricProps) {
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

function matchesStatusFilter(robot: Robot, statusFilter: StatusFilter) {
  if (statusFilter === "all") {
    return true;
  }
  if (statusFilter === "online") {
    return robot.is_online;
  }
  if (statusFilter === "offline") {
    return !robot.is_online;
  }
  if (statusFilter === "running") {
    return robot.is_online && robot.status === "running";
  }
  return robot.is_online && robot.status === "idle";
}

function StatusPill({ online }: { online: boolean }) {
  return (
    <span className={`pill ${online ? "pill-online" : "pill-offline"}`}>
      {online ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
      {online ? "online" : "offline"}
    </span>
  );
}

function BatteryCell({ level }: { level: number | null }) {
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

function formatLastSeen(seconds: number | null) {
  if (seconds === null) {
    return "never";
  }
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export default App;
