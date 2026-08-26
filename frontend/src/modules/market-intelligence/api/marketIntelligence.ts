import { authenticatedFetch } from "../../../auth/session";
import type {
  AgentTask,
  MarketOverview,
  MarketIntelligenceRequest,
  TaskCreate,
  TaskEvent,
  TaskPreviewRequest,
  TaskPreviewResponse,
} from "../types/marketIntelligence";

const basePath = "/api/v1/agent/tasks";

export class MarketIntelligenceApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(message);
  }
}

async function parseError(response: Response): Promise<MarketIntelligenceApiError> {
  let detail: unknown;
  try {
    detail = (await response.json() as { detail?: unknown }).detail;
  } catch {
    detail = null;
  }
  const message =
    typeof detail === "string"
      ? detail
      : typeof detail === "object" && detail && "message" in detail
        ? String((detail as { message: unknown }).message)
        : `请求失败（${response.status}）`;
  return new MarketIntelligenceApiError(message, response.status, detail);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body) headers.set("Content-Type", "application/json");
  const response = await authenticatedFetch(path, { ...options, headers });
  if (!response.ok) throw await parseError(response);
  return response.json() as Promise<T>;
}

export function previewMarketTask(userQuery: string): Promise<TaskPreviewResponse> {
  const payload: TaskPreviewRequest = {
    schema_version: "1.0",
    user_query: userQuery,
    intent: "market_entry",
  };
  return request<TaskPreviewResponse>(`${basePath}/preview`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createMarketIntelligenceTask(
  userQuery: string,
  input: MarketIntelligenceRequest,
): Promise<AgentTask> {
  const payload: TaskCreate = {
    user_query: userQuery,
    intent: "market_entry",
    business_context: {
      schema_version: "1.0",
      market_intelligence_request: input,
    },
    constraints: {},
    priority: "HIGH",
  };
  return request<AgentTask>(basePath, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMarketTask(taskId: string): Promise<AgentTask> {
  return request<AgentTask>(`${basePath}/${encodeURIComponent(taskId)}`);
}

export function getMarketOverview(market = "US"): Promise<MarketOverview> {
  return request<MarketOverview>(`/api/v1/analytics/market?market=${encodeURIComponent(market)}`);
}

export function cancelMarketTask(taskId: string): Promise<AgentTask> {
  return request<AgentTask>(`${basePath}/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
  });
}

export async function streamMarketTaskEvents(
  taskId: string,
  options: {
    signal: AbortSignal;
    lastEventId?: string;
    onEvent: (event: TaskEvent) => void;
  },
): Promise<void> {
  const headers = new Headers({ Accept: "text/event-stream" });
  if (options.lastEventId) headers.set("Last-Event-ID", options.lastEventId);
  const response = await authenticatedFetch(`${basePath}/${encodeURIComponent(taskId)}/events`, {
    headers,
    signal: options.signal,
  });
  if (!response.ok) throw await parseError(response);
  if (!response.body) throw new Error("浏览器无法读取任务事件流");

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += value.replaceAll("\r\n", "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (data) options.onEvent(JSON.parse(data) as TaskEvent);
      boundary = buffer.indexOf("\n\n");
    }
  }
}
