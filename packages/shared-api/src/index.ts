import type { AgentTaskSummary } from "@ecommerce-agent/shared-contracts";

export type TaskListResponse = { items: AgentTaskSummary[]; total: number };

export const apiPaths = {
  tasks: "/api/v1/agent/tasks",
  approvals: "/api/v1/approvals",
  dashboard: "/api/v1/dashboard/overview",
  knowledgeSearch: "/api/v1/knowledge/search",
} as const;
