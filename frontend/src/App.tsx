import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  Battery,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  CirclePause,
  CirclePlay,
  RefreshCw,
  Search,
  Wifi,
  WifiOff
} from "lucide-react";

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
  pagination: Pagination;
  summary: FleetSummary;
};

type StatusFilter = "all" | "online" | "offline" | "running" | "idle";

type Pagination = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type FleetSummary = {
  total: number;
  online: number;
  offline: number;
  running: number;
  idle: number;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const pageSizeOptions = [10, 25, 50, 100];
const initialPagination: Pagination = {
  total: 0,
  page: 1,
  page_size: 25,
  total_pages: 1
};
const initialSummary: FleetSummary = {
  total: 0,
  online: 0,
  offline: 0,
  running: 0,
  idle: 0
};

function App() {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [summary, setSummary] = useState<FleetSummary>(initialSummary);
  const [pagination, setPagination] = useState<Pagination>(initialPagination);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const loadRobots = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams({
        page: String(currentPage),
        page_size: String(pageSize),
        filter: statusFilter
      });
      const normalizedSearch = searchTerm.trim();
      if (normalizedSearch.length > 0) {
        params.set("search", normalizedSearch);
      }

      const response = await fetch(`${apiBaseUrl}/robots/status?${params}`);
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      const data = (await response.json()) as RobotsResponse;
      setRobots(data.robots);
      setSummary(data.summary);
      setPagination(data.pagination);
      if (data.pagination.page !== currentPage) {
        setCurrentPage(data.pagination.page);
      }
      setLastUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load robot status");
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize, searchTerm, statusFilter]);

  useEffect(() => {
    void loadRobots();
    const intervalId = window.setInterval(() => void loadRobots(), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadRobots]);

  const firstVisibleRow = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.page_size + 1;
  const lastVisibleRow = Math.min(pagination.page * pagination.page_size, pagination.total);

  const updateSearchTerm = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const updateStatusFilter = (nextFilter: StatusFilter) => {
    setStatusFilter((currentFilter) => (currentFilter === nextFilter && nextFilter !== "all" ? "all" : nextFilter));
    setCurrentPage(1);
  };

  const updatePageSize = (value: string) => {
    setPageSize(Number(value));
    setCurrentPage(1);
  };

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
          onClick={() => updateStatusFilter("all")}
        />
        <Metric
          label="Online"
          value={summary.online}
          tone="green"
          icon={<Wifi size={18} />}
          isActive={statusFilter === "online"}
          onClick={() => updateStatusFilter("online")}
        />
        <Metric
          label="Offline"
          value={summary.offline}
          tone="red"
          icon={<WifiOff size={18} />}
          isActive={statusFilter === "offline"}
          onClick={() => updateStatusFilter("offline")}
        />
        <Metric
          label="Running"
          value={summary.running}
          tone="amber"
          icon={<CirclePlay size={18} />}
          isActive={statusFilter === "running"}
          onClick={() => updateStatusFilter("running")}
        />
        <Metric
          label="Idle"
          value={summary.idle}
          tone="slate"
          icon={<CirclePause size={18} />}
          isActive={statusFilter === "idle"}
          onClick={() => updateStatusFilter("idle")}
        />
      </section>

      {error ? <div className="notice error">{error}</div> : null}

      <section className="tableSection" aria-label="Robot status table">
        <div className="sectionHeader">
          <h2>Robots</h2>
          <span>{isLoading ? "Loading" : `${pagination.total} matching of ${summary.total} tracked`}</span>
        </div>

        <div className="tableTools">
          <label className="searchBox">
            <Search size={16} aria-hidden="true" />
            <span className="srOnly">Search robots</span>
            <input
              value={searchTerm}
              onChange={(event) => updateSearchTerm(event.target.value)}
              placeholder="Search robot ID"
              type="search"
            />
          </label>
          <label className="pageSizeControl">
            <span>Rows per page</span>
            <select value={pageSize} onChange={(event) => updatePageSize(event.target.value)}>
              {pageSizeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
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
              {robots.map((robot) => (
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
          {!isLoading && summary.total === 0 ? <div className="emptyState">No robots have checked in yet.</div> : null}
          {!isLoading && summary.total > 0 && pagination.total === 0 ? <div className="emptyState">No robots match the current filters.</div> : null}
        </div>

        <div className="paginationBar" aria-label="Robot table pagination">
          <span>
            Rows {firstVisibleRow}-{lastVisibleRow} of {pagination.total}
          </span>
          <div className="paginationControls">
            <button
              className="pageButton"
              onClick={() => setCurrentPage(1)}
              disabled={pagination.page <= 1}
              title="First page"
              aria-label="First page"
              type="button"
            >
              <ChevronsLeft size={17} aria-hidden="true" />
            </button>
            <button
              className="pageButton"
              onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
              disabled={pagination.page <= 1}
              title="Previous page"
              aria-label="Previous page"
              type="button"
            >
              <ChevronLeft size={17} aria-hidden="true" />
            </button>
            <span className="pageCount">
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <button
              className="pageButton"
              onClick={() => setCurrentPage((page) => Math.min(pagination.total_pages, page + 1))}
              disabled={pagination.page >= pagination.total_pages}
              title="Next page"
              aria-label="Next page"
              type="button"
            >
              <ChevronRight size={17} aria-hidden="true" />
            </button>
            <button
              className="pageButton"
              onClick={() => setCurrentPage(pagination.total_pages)}
              disabled={pagination.page >= pagination.total_pages}
              title="Last page"
              aria-label="Last page"
              type="button"
            >
              <ChevronsRight size={17} aria-hidden="true" />
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
