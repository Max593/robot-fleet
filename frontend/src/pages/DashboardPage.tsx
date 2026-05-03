import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BatteryCharging,
  CirclePause,
  CirclePlay,
  OctagonPause,
  Search,
  Terminal,
  Wifi,
  WifiOff,
  X
} from "lucide-react";
import { getFleetStatus } from "../api/robots";
import { initialPagination, initialSummary, pageSizeOptions } from "../constants";
import { BatteryCell } from "../components/BatteryCell";
import { Metric } from "../components/Metric";
import { PaginationBar } from "../components/PaginationBar";
import { StatusPill } from "../components/StatusPill";
import { TopbarActions } from "../components/TopbarActions";
import type { FleetSummary, Pagination, Robot, StatusFilter, Theme } from "../types";
import { formatLastSeen } from "../utils/format";
import { useDebouncedValue } from "../utils/useDebouncedValue";

type DashboardPageProps = {
  lastUpdatedAt: Date | null;
  theme: Theme;
  onNavigateToRobot: (robotId: string) => void;
  onOpenCommand: (robot: Robot) => void;
  onRefreshTime: (updatedAt: Date) => void;
  onToggleTheme: () => void;
};

export function DashboardPage({
  lastUpdatedAt,
  theme,
  onNavigateToRobot,
  onOpenCommand,
  onRefreshTime,
  onToggleTheme
}: DashboardPageProps) {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [summary, setSummary] = useState<FleetSummary>(initialSummary);
  const [pagination, setPagination] = useState<Pagination>(initialPagination);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const debouncedSearchTerm = useDebouncedValue(searchTerm, 300);

  const loadRobots = useCallback(async () => {
    try {
      setError(null);
      const data = await getFleetStatus({
        page: currentPage,
        pageSize,
        filter: statusFilter,
        search: debouncedSearchTerm
      });
      setRobots(data.robots);
      setSummary(data.summary);
      setPagination(data.pagination);
      if (data.pagination.page !== currentPage) {
        setCurrentPage(data.pagination.page);
      }
      onRefreshTime(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load robot status");
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, debouncedSearchTerm, onRefreshTime, pageSize, statusFilter]);

  useEffect(() => {
    void loadRobots();
    const intervalId = window.setInterval(() => void loadRobots(), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadRobots]);

  const updateSearchTerm = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const clearSearchTerm = () => {
    setSearchTerm("");
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
    <>
      <section className="topbar" aria-label="Fleet overview">
        <div>
          <p className="eyebrow">Local Robot Fleet</p>
          <h1>Operations Dashboard</h1>
        </div>
        <TopbarActions
          lastUpdatedAt={lastUpdatedAt}
          theme={theme}
          refreshLabel="Refresh fleet status"
          onRefresh={() => void loadRobots()}
          onToggleTheme={onToggleTheme}
        />
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
        <Metric
          label="Charging"
          value={summary.charging}
          tone="cyan"
          icon={<BatteryCharging size={18} />}
          isActive={statusFilter === "charging"}
          onClick={() => updateStatusFilter("charging")}
        />
        <Metric
          label="Paused"
          value={summary.paused}
          tone="purple"
          icon={<OctagonPause size={18} />}
          isActive={statusFilter === "paused"}
          onClick={() => updateStatusFilter("paused")}
        />
      </section>

      {error ? <div className="notice error">{error}</div> : null}

      <section className="tableSection" aria-label="Robot status table">
        <div className="sectionHeader">
          <h2>Robots</h2>
          <span>{isLoading ? "Loading" : `${pagination.total} matching of ${summary.total} tracked`}</span>
        </div>

        <div className="tableTools">
          <div className="searchControls">
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
            <button
              className="clearSearchButton"
              type="button"
              onClick={clearSearchTerm}
              disabled={searchTerm.length === 0}
              aria-label="Clear robot search"
            >
              <X size={15} aria-hidden="true" />
              Clear
            </button>
          </div>
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
                <th>Last check-in</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {robots.map((robot) => (
                <tr
                  className="clickableRow"
                  key={robot.robot_id}
                  onClick={() => onNavigateToRobot(robot.robot_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onNavigateToRobot(robot.robot_id);
                    }
                  }}
                  tabIndex={0}
                  title={`Open ${robot.robot_id}`}
                >
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
                  <td>
                    <button
                      className="commandButton"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onOpenCommand(robot);
                      }}
                    >
                      <Terminal size={15} aria-hidden="true" />
                      Command
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && summary.total === 0 ? <div className="emptyState">No robots have checked in yet.</div> : null}
          {!isLoading && summary.total > 0 && pagination.total === 0 ? <div className="emptyState">No robots match the current filters.</div> : null}
        </div>

        <PaginationBar label="Robot table pagination" pagination={pagination} onPageChange={setCurrentPage} />
      </section>
    </>
  );
}
