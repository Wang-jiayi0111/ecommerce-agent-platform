export type TaskStatus =
  | "PENDING"
  | "PLANNING"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "RETRYING"
  | "DEGRADED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type TaskIntent =
  | "market_entry"
  | "product_strategy"
  | "listing_generation"
  | "operations_diagnosis";

export type AgentTaskSummary = {
  id: string;
  traceId: string;
  userQuery: string;
  intent: TaskIntent;
  status: TaskStatus;
  approvalStatus: string;
};
