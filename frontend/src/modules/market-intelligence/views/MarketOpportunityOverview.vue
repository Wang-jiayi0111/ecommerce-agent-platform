<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { getMarketOverview } from "../api/marketIntelligence";
import type {
  EntryDecision,
  MarketOverview,
  MarketOverviewStageStatus,
  TaskStatus,
} from "../types/marketIntelligence";

const emit = defineEmits<{
  create: [];
  task: [taskId: string];
}>();

const overview = ref<MarketOverview | null>(null);
const loading = ref(true);
const error = ref("");

const decisionCopy: Record<EntryDecision, string> = {
  GO: "建议进入",
  CONDITIONAL_GO: "有条件进入",
  NO_GO: "暂不进入",
  INSUFFICIENT_DATA: "信息不足",
};
const taskStatusCopy: Record<TaskStatus, string> = {
  PENDING: "等待执行",
  PLANNING: "规划中",
  RUNNING: "执行中",
  WAITING_APPROVAL: "等待审批",
  RETRYING: "正在重试",
  DEGRADED: "降级完成",
  COMPLETED: "已完成",
  FAILED: "执行失败",
  CANCELLED: "已取消",
};
const stageStatusCopy: Record<MarketOverviewStageStatus, string> = {
  pending: "等待执行",
  running: "执行中",
  completed: "已完成",
  partial: "部分完成",
  failed: "执行失败",
};

const latestDecision = computed(() => {
  const assessment = overview.value?.latest_assessment;
  return assessment ? decisionCopy[assessment.decision] : "暂无报告";
});

async function loadOverview() {
  loading.value = true;
  error.value = "";
  try {
    overview.value = await getMarketOverview();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "市场概览加载失败";
  } finally {
    loading.value = false;
  }
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );
}

onMounted(() => void loadOverview());
</script>

<template>
  <main class="overview-shell">
    <header class="overview-header">
      <div>
        <span>MARKET OPPORTUNITY</span>
        <h1>市场机会</h1>
        <p>基于已登记数据集和历史分析任务，查看当前可分析类目、样本覆盖与最新进入建议。</p>
      </div>
      <button type="button" class="create-button" @click="emit('create')">
        ＋ 创建市场分析
      </button>
    </header>

    <div v-if="loading" class="state-card" aria-live="polite">正在读取真实市场数据…</div>
    <div v-else-if="error" class="state-card error" role="alert">
      <span>{{ error }}</span><button type="button" @click="loadOverview">重新加载</button>
    </div>

    <template v-else-if="overview">
      <section class="metric-row" aria-label="市场数据概览">
        <article>
          <span>监测类目</span>
          <strong>{{ overview.monitored_category_count }}</strong>
          <small>{{ overview.datasets.length }} 个有效数据集</small>
        </article>
        <article>
          <span>竞品样本</span>
          <strong>{{ overview.competitor_sample_count.toLocaleString("zh-CN") }}</strong>
          <small>{{ overview.review_sample_count.toLocaleString("zh-CN") }} 条评论样本</small>
        </article>
        <article class="decision-metric">
          <span>最新进入建议</span>
          <strong>{{ latestDecision }}</strong>
          <small v-if="overview.latest_assessment">
            {{ dateTime(overview.latest_assessment.generated_at) }} · {{ overview.latest_assessment.report_status }}
          </small>
          <small v-else>完成一次市场分析后生成</small>
        </article>
      </section>

      <section v-if="overview.latest_assessment" class="assessment-banner">
        <div>
          <span>最新报告结论</span>
          <strong>{{ decisionCopy[overview.latest_assessment.decision] }}</strong>
        </div>
        <p>{{ overview.latest_assessment.summary }}</p>
        <button type="button" @click="emit('task', overview.latest_assessment.task_id)">查看完整报告 →</button>
      </section>

      <section class="overview-section">
        <div class="section-heading">
          <div><span>01</span><h2>当前数据能力</h2></div>
          <small>概览更新于 {{ dateTime(overview.generated_at) }}</small>
        </div>
        <div class="capability-grid">
          <article>
            <div class="capability-icon">M</div>
            <span>类目扫描</span>
            <strong>{{ overview.available_metric_count }} 项指标可用</strong>
            <p>{{ overview.partial_metric_count }} 项指标部分可用，统计范围来自有效固定数据集。</p>
          </article>
          <article>
            <div class="capability-icon">C</div>
            <span>竞品拆解</span>
            <strong>{{ overview.competitor_sample_count.toLocaleString("zh-CN") }} 个商品</strong>
            <p>同时覆盖 {{ overview.review_sample_count.toLocaleString("zh-CN") }} 条评论，可用于竞品和用户反馈分析。</p>
          </article>
          <article>
            <div class="capability-icon">P</div>
            <span>利润约束</span>
            <strong>{{ overview.profit_ready_dataset_count ? "已有成本数据" : "等待成本输入" }}</strong>
            <p>利润计算使用任务提交时的售价、成本、平台费用和最低毛利要求。</p>
          </article>
        </div>
      </section>

      <div class="overview-columns">
        <section class="overview-section">
          <div class="section-heading"><div><span>02</span><h2>有效数据集</h2></div></div>
          <div v-if="overview.datasets.length" class="dataset-list">
            <article v-for="dataset in overview.datasets" :key="dataset.dataset_id">
              <div>
                <span>{{ dataset.platform }} · {{ dataset.market }}</span>
                <h3>{{ dataset.display_name }}</h3>
                <p>{{ dataset.category }} · {{ dataset.keyword }}</p>
              </div>
              <dl>
                <div><dt>商品</dt><dd>{{ dataset.product_count.toLocaleString("zh-CN") }}</dd></div>
                <div><dt>评论</dt><dd>{{ dataset.review_count.toLocaleString("zh-CN") }}</dd></div>
                <div><dt>数据截止</dt><dd>{{ dateTime(dataset.source_timestamp) }}</dd></div>
              </dl>
            </article>
          </div>
          <p v-else class="empty">当前市场没有通过校验的可用数据集。</p>
        </section>

        <section class="overview-section">
          <div class="section-heading">
            <div><span>03</span><h2>标准执行链路</h2></div>
            <small>{{ overview.latest_task ? "最近任务状态" : "尚无执行记录" }}</small>
          </div>
          <ol class="pipeline-list">
            <li v-for="(stage, index) in overview.pipeline" :key="stage.code" :class="stage.status">
              <i>{{ index + 1 }}</i>
              <div><strong>{{ stage.label }}</strong><p>{{ stage.description }}</p></div>
              <span>{{ stageStatusCopy[stage.status] }}</span>
            </li>
          </ol>
        </section>
      </div>

      <section class="overview-section recent-section">
        <div class="section-heading"><div><span>04</span><h2>最近市场分析</h2></div></div>
        <div v-if="overview.recent_tasks.length" class="recent-list">
          <button
            v-for="task in overview.recent_tasks"
            :key="task.task_id"
            type="button"
            @click="emit('task', task.task_id)"
          >
            <span :class="`task-status ${task.status.toLowerCase()}`">{{ taskStatusCopy[task.status] }}</span>
            <strong>{{ task.query }}</strong>
            <small>{{ dateTime(task.created_at) }}</small>
            <i>查看任务 →</i>
          </button>
        </div>
        <div v-else class="empty-action">
          <p>还没有市场分析记录。</p>
          <button type="button" @click="emit('create')">创建第一次市场分析</button>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.overview-shell { --ink: #18233c; --muted: #6f7c92; max-width: 1320px; margin: 0 auto; padding-bottom: 2rem; color: var(--ink); }
.overview-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 2rem; padding: 0.8rem 0 1.2rem; }
.overview-header > div > span { color: #526a9f; font-size: 0.68rem; font-weight: 800; letter-spacing: 0.15em; }
.overview-header h1 { margin: 0.3rem 0; font-size: clamp(1.8rem, 3vw, 2.55rem); letter-spacing: -0.035em; }
.overview-header p { max-width: 720px; margin: 0; color: var(--muted); line-height: 1.6; }
.create-button { flex: 0 0 auto; padding: 0.72rem 1rem; color: #fff; background: #3456b2; border: 0; border-radius: 10px; font-weight: 750; box-shadow: 0 8px 20px rgb(52 86 178 / 20%); }
.state-card { padding: 2rem; color: var(--muted); background: #fff; border: 1px solid #dfe5ed; border-radius: 14px; text-align: center; }
.state-card.error { display: flex; justify-content: space-between; color: #793943; background: #fff8f8; border-color: #ebc9cd; }
.state-card button { color: inherit; background: transparent; border: 0; font-weight: 700; }
.metric-row { display: grid; grid-template-columns: repeat(3, 1fr); overflow: hidden; background: #fff; border: 1px solid #dde3ec; border-radius: 16px; }
.metric-row article { display: flex; min-width: 0; padding: 1.25rem 1.4rem; border-right: 1px solid #e4e8ef; flex-direction: column; }
.metric-row article:last-child { border: 0; }
.metric-row span { color: #748198; font-size: 0.7rem; font-weight: 700; }
.metric-row strong { margin: 0.25rem 0; font-size: 1.65rem; }
.metric-row small { overflow: hidden; color: #8994a7; font-size: 0.67rem; text-overflow: ellipsis; white-space: nowrap; }
.decision-metric strong { color: #31559c; font-size: 1.25rem; }
.assessment-banner { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 1.2rem; margin-top: 1rem; padding: 1rem 1.2rem; color: #284c3c; background: #e8f5ee; border: 1px solid #c7e5d5; border-radius: 13px; }
.assessment-banner > div { display: flex; flex-direction: column; }
.assessment-banner span { font-size: 0.6rem; font-weight: 750; }
.assessment-banner strong { margin-top: 0.15rem; font-size: 0.9rem; }
.assessment-banner p { margin: 0; font-size: 0.72rem; line-height: 1.5; }
.assessment-banner button { color: inherit; background: transparent; border: 0; font-size: 0.67rem; font-weight: 750; white-space: nowrap; }
.overview-section { margin-top: 1rem; padding: 1.25rem; background: #fff; border: 1px solid #dfe5ed; border-radius: 15px; }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.section-heading > div { display: flex; align-items: baseline; gap: 0.6rem; }
.section-heading span { color: #8b97aa; font-size: 0.68rem; font-weight: 800; }
.section-heading h2 { margin: 0; font-size: 1rem; }
.section-heading small { color: #8a95a7; font-size: 0.65rem; }
.capability-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
.capability-grid article { padding: 1rem; background: #f6f8fb; border: 1px solid #e6eaf0; border-radius: 11px; }
.capability-icon { display: grid; width: 30px; height: 30px; margin-bottom: 0.7rem; color: #3d5ba9; background: #e5eafb; border-radius: 8px; place-items: center; font-size: 0.67rem; font-weight: 850; }
.capability-grid span { color: #7b879b; font-size: 0.65rem; }
.capability-grid strong { display: block; margin-top: 0.2rem; font-size: 0.9rem; }
.capability-grid p { margin: 0.35rem 0 0; color: #788499; font-size: 0.68rem; line-height: 1.5; }
.overview-columns { display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 1rem; }
.dataset-list { display: grid; gap: 0.65rem; }
.dataset-list article { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; padding: 0.85rem; background: #f7f9fc; border-radius: 10px; }
.dataset-list span { color: #687895; font-size: 0.62rem; font-weight: 800; text-transform: uppercase; }
.dataset-list h3 { margin: 0.2rem 0; font-size: 0.85rem; }
.dataset-list p { margin: 0; color: #8792a5; font-size: 0.67rem; }
.dataset-list dl { display: flex; align-items: center; gap: 1rem; margin: 0; }
.dataset-list dl div { display: flex; flex-direction: column; }
.dataset-list dt { color: #8b96a8; font-size: 0.58rem; }
.dataset-list dd { margin: 0.15rem 0 0; font-size: 0.68rem; font-weight: 750; white-space: nowrap; }
.pipeline-list { margin: 0; padding: 0; list-style: none; }
.pipeline-list li { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; align-items: center; gap: 0.65rem; padding: 0.65rem 0; border-bottom: 1px solid #edf0f4; }
.pipeline-list li:last-child { border: 0; }
.pipeline-list i { display: grid; width: 24px; height: 24px; color: #77859b; background: #edf0f5; border-radius: 50%; place-items: center; font-size: 0.6rem; font-style: normal; }
.pipeline-list strong { font-size: 0.75rem; }
.pipeline-list p { margin: 0.12rem 0 0; color: #8792a5; font-size: 0.63rem; }
.pipeline-list > li > span { padding: 0.2rem 0.4rem; color: #778399; background: #eef1f5; border-radius: 4px; font-size: 0.58rem; }
.pipeline-list li.completed i, .pipeline-list li.completed > span { color: #246247; background: #e2f3ea; }
.pipeline-list li.running i, .pipeline-list li.running > span { color: #3159a7; background: #e6edff; }
.pipeline-list li.failed i, .pipeline-list li.failed > span { color: #893e47; background: #fbe8ea; }
.recent-list { display: grid; gap: 0.55rem; }
.recent-list > button { display: grid; width: 100%; grid-template-columns: auto minmax(0, 1fr) auto auto; align-items: center; gap: 0.8rem; padding: 0.75rem; color: var(--ink); text-align: left; background: #f7f9fc; border: 1px solid #e7eaf0; border-radius: 9px; }
.recent-list > button:hover { border-color: #bdc9e2; }
.recent-list strong { overflow: hidden; font-size: 0.73rem; text-overflow: ellipsis; white-space: nowrap; }
.recent-list small { color: #8b96a8; font-size: 0.62rem; }
.recent-list i { color: #4260af; font-size: 0.62rem; font-style: normal; }
.task-status { padding: 0.2rem 0.4rem; color: #59677e; background: #e9edf3; border-radius: 4px; font-size: 0.58rem; }
.task-status.completed { color: #246247; background: #e2f3ea; }
.task-status.degraded { color: #795c1d; background: #fff1ca; }
.task-status.failed { color: #893e47; background: #fbe8ea; }
.empty, .empty-action { margin: 0; padding: 1.4rem; color: #8792a5; background: #f7f8fa; border-radius: 9px; text-align: center; font-size: 0.72rem; }
.empty-action p { margin: 0 0 0.5rem; }
.empty-action button { color: #3655b3; background: transparent; border: 0; font-weight: 750; }
@media (max-width: 991px) { .overview-columns { grid-template-columns: 1fr; } .dataset-list article { grid-template-columns: 1fr; } }
@media (max-width: 767px) { .overview-header { align-items: stretch; flex-direction: column; } .metric-row, .capability-grid, .assessment-banner { grid-template-columns: 1fr; } .metric-row article { border-right: 0; border-bottom: 1px solid #e4e8ef; } .create-button { width: 100%; } .assessment-banner button { justify-self: start; padding: 0; } }
@media (max-width: 575px) { .section-heading { align-items: flex-start; flex-direction: column; } .dataset-list dl { align-items: flex-start; flex-direction: column; gap: 0.45rem; } .recent-list > button { grid-template-columns: auto 1fr; } .recent-list small, .recent-list i { grid-column: 2; } }
</style>
