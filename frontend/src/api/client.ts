const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = {
  notFoundMessage?: string;
};

export async function requestJson<T>(path: string, init?: RequestInit, options?: RequestOptions): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  if (!response.ok) {
    if (response.status === 404 && options?.notFoundMessage) {
      throw new Error(options.notFoundMessage);
    }
    throw new Error(`Backend returned ${response.status}`);
  }
  return (await response.json()) as T;
}
