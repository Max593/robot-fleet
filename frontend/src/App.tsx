import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  ArrowLeft,
  Battery,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  CirclePause,
  CirclePlay,
  Moon,
  RefreshCw,
  Search,
  Send,
  Sun,
  Terminal,
  Wifi,
  WifiOff,
  X
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

type RobotEvent = {
  id: number;
  robot_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type RobotEventsResponse = {
  events: RobotEvent[];
  pagination: Pagination;
};

type RobotCommand = {
  id: number;
  robot_id: string;
  command_type: CommandType;
  payload: Record<string, unknown>;
  status: "pending" | "claimed" | "completed" | "failed" | "expired" | "cancelled";
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  claimed_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
};

type RobotCommandsResponse = {
  commands: RobotCommand[];
  pagination: Pagination;
};

type StatusFilter = "all" | "online" | "offline" | "running" | "idle";
type CommandType =
  | "run_diagnostic"
  | "pause_for"
  | "pause_until_resumed"
  | "resume"
  | "return_to_base"
  | "recharge_to_full";

type Toast = {
  id: number;
  message: string;
};

type Theme = "light" | "dark";

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
const detailPageSize = 25;
const pauseDurationOptions = [30, 60, 120, 300];
const commandLabels: Record<CommandType, string> = {
  run_diagnostic: "Run diagnostic",
  pause_for: "Pause for",
  pause_until_resumed: "Pause until resumed",
  resume: "Resume",
  return_to_base: "Return to base",
  recharge_to_full: "Recharge to full"
};
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

function getInitialTheme(): Theme {
  const storedTheme = window.localStorage.getItem("robot-fleet-theme");
  return storedTheme === "dark" ? "dark" : "light";
}

function getRouteRobotId() {
  const match = window.location.pathname.match(/^\/robots\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}

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
  const [selectedRobot, setSelectedRobot] = useState<Robot | null>(null);
  const [selectedCommand, setSelectedCommand] = useState<CommandType>("run_diagnostic");
  const [pauseDuration, setPauseDuration] = useState(30);
  const [isSendingCommand, setIsSendingCommand] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [routeRobotId, setRouteRobotId] = useState<string | null>(getRouteRobotId);
  const [commandRefreshSignal, setCommandRefreshSignal] = useState(0);

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
    if (routeRobotId !== null) {
      return undefined;
    }

    void loadRobots();
    const intervalId = window.setInterval(() => void loadRobots(), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadRobots, routeRobotId]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("robot-fleet-theme", theme);
  }, [theme]);

  useEffect(() => {
    const handlePopState = () => setRouteRobotId(getRouteRobotId());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const firstVisibleRow = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.page_size + 1;
  const lastVisibleRow = Math.min(pagination.page * pagination.page_size, pagination.total);

  const navigateToRobot = (robotId: string) => {
    window.history.pushState(null, "", `/robots/${encodeURIComponent(robotId)}`);
    setRouteRobotId(robotId);
  };

  const navigateToDashboard = () => {
    window.history.pushState(null, "", "/");
    setRouteRobotId(null);
  };

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

  const dismissToast = useCallback((toastId: number) => {
    setToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== toastId));
  }, []);

  const addToast = useCallback(
    (message: string) => {
      const toastId = Date.now() + Math.random();
      setToasts((currentToasts) => [...currentToasts, { id: toastId, message }]);
      window.setTimeout(() => dismissToast(toastId), 10000);
    },
    [dismissToast]
  );

  const openCommandDialog = (robot: Robot) => {
    setSelectedRobot(robot);
    setSelectedCommand("run_diagnostic");
    setPauseDuration(30);
    setCommandError(null);
  };

  const sendCommand = async () => {
    if (selectedRobot === null) {
      return;
    }

    try {
      setIsSendingCommand(true);
      setCommandError(null);
      const payload =
        selectedCommand === "pause_for"
          ? {
              duration_seconds: pauseDuration
            }
          : {};

      const response = await fetch(`${apiBaseUrl}/robots/${selectedRobot.robot_id}/commands`, {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({
          command_type: selectedCommand,
          payload
        })
      });
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      addToast(`${commandLabels[selectedCommand]} queued for ${selectedRobot.robot_id}`);
      setCommandRefreshSignal((currentSignal) => currentSignal + 1);
      setSelectedRobot(null);
    } catch (err) {
      setCommandError(err instanceof Error ? err.message : "Unable to queue command");
    } finally {
      setIsSendingCommand(false);
    }
  };

  const updateLastRefreshTime = useCallback((updatedAt: Date) => {
    setLastUpdatedAt(updatedAt);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }, []);

  return (
    <main className="shell">
      {routeRobotId ? (
        <RobotDetailPage
          robotId={routeRobotId}
          lastUpdatedAt={lastUpdatedAt}
          theme={theme}
          commandRefreshSignal={commandRefreshSignal}
          onBack={navigateToDashboard}
          onOpenCommand={openCommandDialog}
          onRefreshTime={updateLastRefreshTime}
          onToggleTheme={toggleTheme}
        />
      ) : (
        <>
      <section className="topbar" aria-label="Fleet overview">
        <div>
          <p className="eyebrow">Local Robot Fleet</p>
          <h1>Operations Dashboard</h1>
        </div>
        <div className="topbarActions">
          <span className="refreshTime">{lastUpdatedAt ? `Updated ${lastUpdatedAt.toLocaleTimeString()}` : "Waiting for data"}</span>
          <button
            className="iconButton"
            onClick={toggleTheme}
            title={theme === "dark" ? "Use light mode" : "Use dark mode"}
            aria-label={theme === "dark" ? "Use light mode" : "Use dark mode"}
          >
            {theme === "dark" ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
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
            {searchTerm.length > 0 ? (
              <button className="searchClearButton" type="button" onClick={clearSearchTerm} aria-label="Clear robot search">
                <X size={15} aria-hidden="true" />
              </button>
            ) : null}
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
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {robots.map((robot) => (
                <tr
                  className="clickableRow"
                  key={robot.robot_id}
                  onClick={() => navigateToRobot(robot.robot_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigateToRobot(robot.robot_id);
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
                        openCommandDialog(robot);
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
        </>
      )}

      {toasts.length > 0 ? (
        <div className="toastStack" aria-live="polite" aria-label="Notifications">
          {toasts.map((toast) => (
            <div className="toastNotice" role="status" key={toast.id}>
              <span>{toast.message}</span>
              <button type="button" onClick={() => dismissToast(toast.id)} aria-label="Dismiss notification">
                <X size={15} aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      ) : null}

      {selectedRobot ? (
        <div className="modalBackdrop" role="presentation">
          <section className="commandDialog" role="dialog" aria-modal="true" aria-labelledby="commandDialogTitle">
            <div className="dialogHeader">
              <div>
                <p className="eyebrow">Robot Command</p>
                <h2 id="commandDialogTitle">{selectedRobot.robot_id}</h2>
              </div>
              <button className="iconButton" type="button" onClick={() => setSelectedRobot(null)} aria-label="Close command dialog">
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            <label className="fieldControl">
              <span>Command</span>
              <select value={selectedCommand} onChange={(event) => setSelectedCommand(event.target.value as CommandType)}>
                {(Object.keys(commandLabels) as CommandType[]).map((commandType) => (
                  <option key={commandType} value={commandType}>
                    {commandLabels[commandType]}
                  </option>
                ))}
              </select>
            </label>

            {selectedCommand === "pause_for" ? (
              <label className="fieldControl">
                <span>Duration</span>
                <select value={pauseDuration} onChange={(event) => setPauseDuration(Number(event.target.value))}>
                  {pauseDurationOptions.map((duration) => (
                    <option key={duration} value={duration}>
                      {duration}s
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {commandError ? <div className="notice error dialogNotice">{commandError}</div> : null}

            <div className="dialogActions">
              <button className="secondaryButton" type="button" onClick={() => setSelectedRobot(null)}>
                Cancel
              </button>
              <button className="primaryButton" type="button" onClick={() => void sendCommand()} disabled={isSendingCommand}>
                <Send size={16} aria-hidden="true" />
                {isSendingCommand ? "Sending" : "Send"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}

type RobotDetailPageProps = {
  robotId: string;
  lastUpdatedAt: Date | null;
  theme: Theme;
  commandRefreshSignal: number;
  onBack: () => void;
  onOpenCommand: (robot: Robot) => void;
  onRefreshTime: (updatedAt: Date) => void;
  onToggleTheme: () => void;
};

function RobotDetailPage({
  robotId,
  lastUpdatedAt,
  theme,
  commandRefreshSignal,
  onBack,
  onOpenCommand,
  onRefreshTime,
  onToggleTheme
}: RobotDetailPageProps) {
  const [robot, setRobot] = useState<Robot | null>(null);
  const [events, setEvents] = useState<RobotEvent[]>([]);
  const [commands, setCommands] = useState<RobotCommand[]>([]);
  const [eventsPagination, setEventsPagination] = useState<Pagination>(initialPagination);
  const [commandsPagination, setCommandsPagination] = useState<Pagination>(initialPagination);
  const [eventsPage, setEventsPage] = useState(1);
  const [commandsPage, setCommandsPage] = useState(1);
  const [isLoadingDetail, setIsLoadingDetail] = useState(true);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    try {
      setDetailError(null);
      const [robotResponse, eventsResponse, commandsResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/robots/${encodeURIComponent(robotId)}`),
        fetch(`${apiBaseUrl}/robots/${encodeURIComponent(robotId)}/events?page=${eventsPage}&page_size=${detailPageSize}`),
        fetch(`${apiBaseUrl}/robots/${encodeURIComponent(robotId)}/commands?page=${commandsPage}&page_size=${detailPageSize}`)
      ]);

      if (!robotResponse.ok) {
        throw new Error(robotResponse.status === 404 ? "Robot not found" : `Backend returned ${robotResponse.status}`);
      }
      if (!eventsResponse.ok || !commandsResponse.ok) {
        throw new Error("Unable to load robot history");
      }

      const robotData = (await robotResponse.json()) as Robot;
      const eventsData = (await eventsResponse.json()) as RobotEventsResponse;
      const commandsData = (await commandsResponse.json()) as RobotCommandsResponse;

      setRobot(robotData);
      setEvents(eventsData.events);
      setEventsPagination(eventsData.pagination);
      setCommands(commandsData.commands);
      setCommandsPagination(commandsData.pagination);
      if (eventsData.pagination.page !== eventsPage) {
        setEventsPage(eventsData.pagination.page);
      }
      if (commandsData.pagination.page !== commandsPage) {
        setCommandsPage(commandsData.pagination.page);
      }
      onRefreshTime(new Date());
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "Unable to load robot detail");
    } finally {
      setIsLoadingDetail(false);
    }
  }, [commandsPage, eventsPage, onRefreshTime, robotId]);

  useEffect(() => {
    void loadDetail();
    const intervalId = window.setInterval(() => void loadDetail(), 5000);
    return () => window.clearInterval(intervalId);
  }, [loadDetail]);

  useEffect(() => {
    if (commandRefreshSignal > 0) {
      void loadDetail();
    }
  }, [commandRefreshSignal, loadDetail]);

  return (
    <>
      <section className="topbar detailTopbar" aria-label="Robot detail">
        <div className="detailTitle">
          <button className="backButton" type="button" onClick={onBack}>
            <ArrowLeft size={17} aria-hidden="true" />
            Fleet
          </button>
          <div>
            <p className="eyebrow">Robot Detail</p>
            <h1>{robotId}</h1>
          </div>
        </div>
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
          <button className="iconButton" onClick={() => void loadDetail()} title="Refresh robot detail" aria-label="Refresh robot detail">
            <RefreshCw size={18} aria-hidden="true" />
          </button>
        </div>
      </section>

      {detailError ? <div className="notice error">{detailError}</div> : null}

      <section className="detailSummary" aria-label="Robot summary">
        <div className="summaryItem">
          <span>Connectivity</span>
          {robot ? <StatusPill online={robot.is_online} /> : <span className="muted">loading</span>}
        </div>
        <div className="summaryItem">
          <span>Status</span>
          {robot ? <span className={`state state-${robot.status}`}>{robot.status}</span> : <span className="muted">loading</span>}
        </div>
        <div className="summaryItem">
          <span>Battery</span>
          {robot ? <BatteryCell level={robot.battery_level} /> : <span className="muted">loading</span>}
        </div>
        <div className="summaryItem">
          <span>Last seen</span>
          <strong>{robot ? formatLastSeen(robot.last_seen_seconds_ago) : "loading"}</strong>
        </div>
        <div className="summaryItem">
          <span>Last timestamp</span>
          <strong>{robot?.last_seen_at ? formatDateTime(robot.last_seen_at) : "never"}</strong>
        </div>
      </section>

      <div className="detailActions">
        <button className="commandButton" type="button" onClick={() => robot && onOpenCommand(robot)} disabled={robot === null}>
          <Terminal size={15} aria-hidden="true" />
          Command
        </button>
      </div>

      <RobotEventsTable
        events={events}
        isLoading={isLoadingDetail}
        pagination={eventsPagination}
        onPageChange={setEventsPage}
      />
      <RobotCommandsTable
        commands={commands}
        isLoading={isLoadingDetail}
        pagination={commandsPagination}
        onPageChange={setCommandsPage}
      />
    </>
  );
}

type HistoryTableProps = {
  isLoading: boolean;
  pagination: Pagination;
  onPageChange: (page: number) => void;
};

function RobotEventsTable({
  events,
  isLoading,
  pagination,
  onPageChange
}: HistoryTableProps & { events: RobotEvent[] }) {
  return (
    <section className="tableSection" aria-label="Robot event log">
      <div className="sectionHeader">
        <h2>Event Log</h2>
        <span>{isLoading ? "Loading" : `${pagination.total} retained events`}</span>
      </div>
      <div className="tableWrap">
        <table className="historyTable">
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Payload</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{formatDateTime(event.created_at)}</td>
                <td>
                  <span className="eventType">{formatSnakeCase(event.event_type)}</span>
                </td>
                <td>
                  <code className="jsonPayload">{formatJson(event.payload)}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && events.length === 0 ? <div className="emptyState">No retained events for this robot.</div> : null}
      </div>
      <HistoryPagination pagination={pagination} onPageChange={onPageChange} />
    </section>
  );
}

function RobotCommandsTable({
  commands,
  isLoading,
  pagination,
  onPageChange
}: HistoryTableProps & { commands: RobotCommand[] }) {
  return (
    <section className="tableSection" aria-label="Robot command history">
      <div className="sectionHeader">
        <h2>Command History</h2>
        <span>{isLoading ? "Loading" : `${pagination.total} retained commands`}</span>
      </div>
      <div className="tableWrap">
        <table className="historyTable">
          <thead>
            <tr>
              <th>Created</th>
              <th>Command</th>
              <th>Status</th>
              <th>Payload</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {commands.map((command) => (
              <tr key={command.id}>
                <td>{formatDateTime(command.created_at)}</td>
                <td>{commandLabels[command.command_type]}</td>
                <td>
                  <span className={`commandStatus commandStatus-${command.status}`}>{command.status}</span>
                </td>
                <td>
                  <code className="jsonPayload">{formatJson(command.payload)}</code>
                </td>
                <td>
                  <code className="jsonPayload">
                    {command.error_message ?? (command.result ? formatJson(command.result) : "pending")}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && commands.length === 0 ? <div className="emptyState">No commands have been queued for this robot.</div> : null}
      </div>
      <HistoryPagination pagination={pagination} onPageChange={onPageChange} />
    </section>
  );
}

function HistoryPagination({ pagination, onPageChange }: { pagination: Pagination; onPageChange: (page: number) => void }) {
  const firstVisibleRow = pagination.total === 0 ? 0 : (pagination.page - 1) * pagination.page_size + 1;
  const lastVisibleRow = Math.min(pagination.page * pagination.page_size, pagination.total);

  return (
    <div className="paginationBar" aria-label="History pagination">
      <span>
        Rows {firstVisibleRow}-{lastVisibleRow} of {pagination.total}
      </span>
      <div className="paginationControls">
        <button
          className="pageButton"
          onClick={() => onPageChange(1)}
          disabled={pagination.page <= 1}
          title="First page"
          aria-label="First page"
          type="button"
        >
          <ChevronsLeft size={17} aria-hidden="true" />
        </button>
        <button
          className="pageButton"
          onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
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
          onClick={() => onPageChange(Math.min(pagination.total_pages, pagination.page + 1))}
          disabled={pagination.page >= pagination.total_pages}
          title="Next page"
          aria-label="Next page"
          type="button"
        >
          <ChevronRight size={17} aria-hidden="true" />
        </button>
        <button
          className="pageButton"
          onClick={() => onPageChange(pagination.total_pages)}
          disabled={pagination.page >= pagination.total_pages}
          title="Last page"
          aria-label="Last page"
          type="button"
        >
          <ChevronsRight size={17} aria-hidden="true" />
        </button>
      </div>
    </div>
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

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatSnakeCase(value: string) {
  return value.replace(/_/g, " ");
}

function formatJson(value: Record<string, unknown>) {
  return JSON.stringify(value);
}

export default App;
