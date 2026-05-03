import { requestJson } from "./client";
import type {
  CommandType,
  Robot,
  RobotCommandsResponse,
  RobotEventsResponse,
  RobotsResponse,
  StatusFilter
} from "../types";

export type FleetStatusParams = {
  page: number;
  pageSize: number;
  filter: StatusFilter;
  search: string;
};

export function getFleetStatus({ page, pageSize, filter, search }: FleetStatusParams) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    filter
  });

  const normalizedSearch = search.trim();
  if (normalizedSearch.length > 0) {
    params.set("search", normalizedSearch);
  }

  return requestJson<RobotsResponse>(`/robots/status?${params}`);
}

export function getRobot(robotId: string) {
  return requestJson<Robot>(`/robots/${encodeURIComponent(robotId)}`, undefined, { notFoundMessage: "Robot not found" });
}

export function getRobotEvents(robotId: string, page: number, pageSize: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  return requestJson<RobotEventsResponse>(`/robots/${encodeURIComponent(robotId)}/events?${params}`);
}

export function getRobotCommands(robotId: string, page: number, pageSize: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  return requestJson<RobotCommandsResponse>(`/robots/${encodeURIComponent(robotId)}/commands?${params}`);
}

export function queueRobotCommand(robotId: string, commandType: CommandType, payload: Record<string, unknown>) {
  return requestJson(`/robots/${encodeURIComponent(robotId)}/commands`, {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({
      command_type: commandType,
      payload
    })
  });
}
