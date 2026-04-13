export interface ClientEnv {
  wsUrl: string;
  apiBaseUrl: string;
  apiKey: string;
}

export function getClientEnv(): ClientEnv {
  return {
    wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws",
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
    apiKey: process.env.NEXT_PUBLIC_API_KEY ?? "",
  };
}

export function buildTutorWsUrl(
  baseWsUrl: string,
  sessionId: string,
  learnerId: string,
  userId: string,
  apiKey?: string,
): string {
  const url = new URL(baseWsUrl);
  url.searchParams.set("session_id", sessionId);
  url.searchParams.set("learner_id", learnerId);
  url.searchParams.set("user_id", userId);
  if (apiKey) {
    url.searchParams.set("api_key", apiKey);
  }
  return url.toString();
}

export function buildApiHeaders(apiKey: string): Record<string, string> {
  if (!apiKey) {
    return {};
  }
  return {
    "x-api-key": apiKey,
  };
}
