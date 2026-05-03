import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Terminal } from "lucide-react";
import { getRobot, getRobotCommands, getRobotEvents } from "../api/robots";
import { commandLabels, detailPageSize, initialPagination } from "../constants";
import { BatteryCell } from "../components/BatteryCell";
import { JsonPreview } from "../components/JsonPreview";
import { PaginationBar } from "../components/PaginationBar";
import { StatusPill } from "../components/StatusPill";
import { TopbarActions } from "../components/TopbarActions";
import type { Pagination, Robot, RobotCommand, RobotEvent, Theme } from "../types";
import { formatDateTime, formatLastSeen, formatSnakeCase } from "../utils/format";

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

export function RobotDetailPage({
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
      const [robotData, eventsData, commandsData] = await Promise.all([
        getRobot(robotId),
        getRobotEvents(robotId, eventsPage, detailPageSize),
        getRobotCommands(robotId, commandsPage, detailPageSize)
      ]);

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
        <TopbarActions
          lastUpdatedAt={lastUpdatedAt}
          theme={theme}
          refreshLabel="Refresh robot detail"
          onRefresh={() => void loadDetail()}
          onToggleTheme={onToggleTheme}
        />
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
          <span>Last check-in</span>
          <strong>{robot ? formatLastSeen(robot.last_seen_seconds_ago) : "loading"}</strong>
        </div>
        <div className="summaryItem">
          <span>Check-in timestamp</span>
          <strong>{robot?.last_seen_at ? formatDateTime(robot.last_seen_at) : "never"}</strong>
        </div>
      </section>

      <div className="detailActions">
        <button className="commandButton" type="button" onClick={() => robot && onOpenCommand(robot)} disabled={robot === null}>
          <Terminal size={15} aria-hidden="true" />
          Command
        </button>
      </div>

      <RobotEventsTable events={events} isLoading={isLoadingDetail} pagination={eventsPagination} onPageChange={setEventsPage} />
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

function RobotEventsTable({ events, isLoading, pagination, onPageChange }: HistoryTableProps & { events: RobotEvent[] }) {
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
                  <JsonPreview value={event.payload} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && events.length === 0 ? <div className="emptyState">No retained events for this robot.</div> : null}
      </div>
      <PaginationBar label="History pagination" pagination={pagination} onPageChange={onPageChange} />
    </section>
  );
}

function RobotCommandsTable({ commands, isLoading, pagination, onPageChange }: HistoryTableProps & { commands: RobotCommand[] }) {
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
              <th>Origin</th>
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
                  <span className={`commandOrigin commandOrigin-${command.origin}`}>{command.origin}</span>
                </td>
                <td>
                  <span className={`commandStatus commandStatus-${command.status}`}>{command.status}</span>
                </td>
                <td>
                  <JsonPreview value={command.payload} />
                </td>
                <td>
                  <JsonPreview value={command.error_message ?? command.result} emptyLabel="pending" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && commands.length === 0 ? <div className="emptyState">No commands have been queued for this robot.</div> : null}
      </div>
      <PaginationBar label="History pagination" pagination={pagination} onPageChange={onPageChange} />
    </section>
  );
}
