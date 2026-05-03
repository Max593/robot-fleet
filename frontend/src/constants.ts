import type { CommandType, FleetSummary, Pagination } from "./types";

export const pageSizeOptions = [10, 25, 50, 100];
export const detailPageSize = 25;
export const pauseDurationOptions = [30, 60, 120, 300];

export const commandLabels: Record<CommandType, string> = {
  run_diagnostic: "Run diagnostic",
  pause_for: "Pause for",
  pause_until_resumed: "Pause until resumed",
  resume: "Resume",
  return_to_base: "Return to base",
  recharge_to_full: "Recharge to full"
};

export const initialPagination: Pagination = {
  total: 0,
  page: 1,
  page_size: 25,
  total_pages: 1
};

export const initialSummary: FleetSummary = {
  total: 0,
  online: 0,
  offline: 0,
  running: 0,
  idle: 0,
  paused: 0,
  charging: 0
};
