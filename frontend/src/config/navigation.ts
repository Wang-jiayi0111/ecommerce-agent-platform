export type NavigationItem = {
  id: string;
  label: string;
  description: string;
  apiModule: string;
};

export const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    label: "经营总览",
    description: "GMV、订单、转化与库存风险",
    apiModule: "dashboard",
  },
  {
    id: "tasks",
    label: "任务中心",
    description: "状态、节点、Trace、审批与恢复",
    apiModule: "task_center",
  },
  {
    id: "market",
    label: "市场进入评估",
    description: "市场、竞品、评论与利润证据",
    apiModule: "market_intelligence",
  },
  {
    id: "strategy",
    label: "商品策略",
    description: "定位、价格、卖点、差异化与风险",
    apiModule: "product_strategy",
  },
  {
    id: "listing",
    label: "Listing",
    description: "结构化生成、事实与平台规则校验",
    apiModule: "listing",
  },
  {
    id: "diagnosis",
    label: "运营诊断",
    description: "销售、流量、转化与库存归因",
    apiModule: "operations_diagnosis",
  },
  {
    id: "knowledge",
    label: "知识库",
    description: "商品事实、平台规则与运营 SOP",
    apiModule: "knowledge_base",
  },
  {
    id: "evaluation",
    label: "评测与追踪",
    description: "Trace、恢复与质量评测",
    apiModule: "evaluation",
  },
];
