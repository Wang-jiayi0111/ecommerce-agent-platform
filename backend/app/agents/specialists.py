from app.agents.specialist_agent import RuleBasedSpecialistAgent, SpecialistProfile


def build_specialists() -> dict[str, RuleBasedSpecialistAgent]:
    return {
        "market_intelligence": RuleBasedSpecialistAgent(
            SpecialistProfile(
                name="market_intelligence",
                result_type="market_entry_report",
                summary="已生成市场、竞品、评论和利润约束的证据化进入评估。",
                default_actions=["补齐授权市场数据后复核类目机会", "确认目标毛利与成本口径"],
            )
        ),
        "product_strategy": RuleBasedSpecialistAgent(
            SpecialistProfile(
                name="product_strategy",
                result_type="product_strategy",
                summary="已生成目标用户、定位、价格带、卖点和风险框架。",
                default_actions=["确认商品事实", "评审差异化卖点"],
                requires_approval=True,
            )
        ),
        "listing": RuleBasedSpecialistAgent(
            SpecialistProfile(
                name="listing",
                result_type="listing",
                summary="已生成待平台规则与事实一致性校验的结构化 Listing。",
                default_actions=["运行平台规则校验", "审批后保存正式商品方案"],
                requires_approval=True,
            )
        ),
        "operations": RuleBasedSpecialistAgent(
            SpecialistProfile(
                name="operations",
                result_type="operations_diagnosis",
                summary="已生成销售、流量、转化和库存异常的分级诊断。",
                default_actions=["核验异常时间窗", "按优先级验证归因假设"],
            )
        ),
    }
