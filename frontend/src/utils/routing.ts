export function getRouteRobotId() {
  const match = window.location.pathname.match(/^\/robots\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}
