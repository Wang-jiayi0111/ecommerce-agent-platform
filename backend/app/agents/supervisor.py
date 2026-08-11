from app.domain import TaskCreate


class SupervisorAgent:
    """只负责意图路由和计划，不直接查库、计算或执行写操作。"""

    routes = {
        "market_entry": "market_intelligence",
        "product_strategy": "product_strategy",
        "listing_generation": "listing",
        "operations_diagnosis": "operations",
    }

    plans = {
        "market_entry": ["collect_market_evidence", "calculate_profit", "judge_evidence"],
        "product_strategy": ["load_market_result", "build_product_strategy", "judge_evidence"],
        "listing_generation": ["load_product_facts", "generate_listing", "policy_check"],
        "operations_diagnosis": ["load_metrics", "calculate_anomalies", "explain_causes"],
    }

    def select(self, task: TaskCreate) -> tuple[str, list[str]]:
        try:
            return self.routes[task.intent], self.plans[task.intent]
        except KeyError as error:
            raise ValueError(f"unsupported intent: {task.intent}") from error
