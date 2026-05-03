export function formatLastSeen(seconds: number | null) {
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

export function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

export function formatSnakeCase(value: string) {
  return value.replace(/_/g, " ");
}

export function formatJson(value: Record<string, unknown>) {
  return JSON.stringify(value);
}
