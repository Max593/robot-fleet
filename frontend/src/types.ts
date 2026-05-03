export type Robot = {
  robot_id: string;
  status: "idle" | "running";
  battery_level: number | null;
  last_seen_at: string | null;
  last_seen_seconds_ago: number | null;
  is_online: boolean;
};

export type Pagination = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type FleetSummary = {
  total: number;
  online: number;
  offline: number;
  running: number;
  idle: number;
};

export type RobotsResponse = {
  robots: Robot[];
  pagination: Pagination;
  summary: FleetSummary;
};

export type RobotEvent = {
  id: number;
  robot_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type RobotEventsResponse = {
  events: RobotEvent[];
  pagination: Pagination;
};

export type CommandType =
  | "run_diagnostic"
  | "pause_for"
  | "pause_until_resumed"
  | "resume"
  | "return_to_base"
  | "recharge_to_full";

export type RobotCommand = {
  id: number;
  robot_id: string;
  command_type: CommandType;
  origin: "operator" | "system";
  payload: Record<string, unknown>;
  status: "pending" | "claimed" | "completed" | "failed" | "expired" | "cancelled";
  result: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  claimed_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
};

export type RobotCommandsResponse = {
  commands: RobotCommand[];
  pagination: Pagination;
};

export type StatusFilter = "all" | "online" | "offline" | "running" | "idle";

export type Theme = "light" | "dark";

export type Toast = {
  id: number;
  message: string;
};
