<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useOperationsWorkspace } from "./composables/useOperationsWorkspace";
import { navigationItems } from "./config/navigation";
import ModuleWorkspace from "./modules/ModuleWorkspace.vue";

const activeModuleId = ref("dashboard");
const selectedShopId = ref("amazon-us-demo");
const currentModule = computed(
  () => navigationItems.find((item) => item.id === activeModuleId.value) ?? navigationItems[0],
);
const isDashboard = computed(() => activeModuleId.value === "dashboard");
const {
  overview,
  tasks,
  pendingTasks,
  loading,
  creating,
  errorMessage,
  dataCutoff,
  loadWorkspace,
  createTask,
} = useOperationsWorkspace();

watch(selectedShopId, (shopId) => loadWorkspace(shopId));

const statusLabels: Record<string, string> = {
  PENDING: "待处理",
  PLANNING: "规划中",
  RUNNING: "运行中",
  WAITING_APPROVAL: "待审批",
  COMPLETED: "已完成",
  DEGRADED: "降级完成",
  FAILED: "失败",
  CANCELLED: "已取消",
};

function statusLabel(value: string) {
  return statusLabels[value] ?? value;
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">A</span><span>Commerce Agent</span></div>
      <label class="shop-switcher">
        <span class="shop-icon">店</span>
        <span><b>Amazon US 演示店</b><small>授权数据环境 · Dev</small></span>
        <select v-model="selectedShopId" aria-label="选择店铺">
          <option value="amazon-us-demo">Amazon US 演示店</option>
          <option value="shopify-demo">Shopify 演示店</option>
        </select>
      </label>
      <nav>
        <button
          v-for="item in navigationItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeModuleId === item.id }"
          @click="activeModuleId = item.id"
        >
          <span class="nav-dot"></span>{{ item.label }}
        </button>
      </nav>
      <div class="sidebar-note">
        <span>治理基线</span>
        <b>Evidence First</b>
        <small>关键结论可追溯，写操作需审批</small>
      </div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <span
          >电商智能运营 / <b>{{ currentModule.label }}</b></span
        >
        <div><span class="environment">DEV</span><span class="user">运营负责人</span></div>
      </header>

      <section class="content">
        <div v-if="isDashboard" class="page-heading">
          <div>
            <p class="eyebrow">OPERATIONS CONTROL CENTER</p>
            <h1>经营总览</h1>
            <p>数据截止 {{ dataCutoff }} · 事实、推断与建议分层展示</p>
          </div>
          <div class="heading-actions">
            <button class="secondary" :disabled="loading" @click="loadWorkspace(selectedShopId)">
              {{ loading ? "加载中…" : "刷新数据" }}
            </button>
            <button class="primary" :disabled="creating" @click="createTask(selectedShopId)">
              {{ creating ? "创建中…" : "+ 市场进入评估" }}
            </button>
          </div>
        </div>

        <div v-if="errorMessage" class="error-state">
          {{ errorMessage }}<button @click="loadWorkspace(selectedShopId)">重新加载</button>
        </div>

        <template v-if="isDashboard && !errorMessage">
          <section class="metric-grid" :class="{ muted: loading }">
            <article v-for="metric in overview?.metrics" :key="metric.code" class="metric-card">
              <span>{{ metric.label }}</span>
              <strong>{{ metric.display_value }}</strong>
              <small :class="metric.trend">{{ metric.change_display }}</small>
            </article>
          </section>

          <section class="dashboard-grid">
            <article class="panel task-panel">
              <div class="panel-heading">
                <div>
                  <h2>Agent 任务</h2>
                  <p>统一状态、证据、审批与 Trace</p>
                </div>
                <button class="link-button" @click="activeModuleId = 'tasks'">任务中心 →</button>
              </div>
              <div class="table-head"><span>任务</span><span>类型</span><span>状态</span></div>
              <div v-if="!tasks.length" class="empty">暂无任务，可发起市场进入评估。</div>
              <div v-for="task in tasks.slice(0, 5)" :key="task.id" class="task-row">
                <span
                  ><b>{{ task.request.user_query }}</b
                  ><small>{{ task.id.slice(0, 8) }} · {{ task.request.user_id }}</small></span
                >
                <span>{{ task.request.intent }}</span>
                <span class="status" :class="task.status.toLowerCase()">{{
                  statusLabel(task.status)
                }}</span>
              </div>
            </article>

            <article class="panel">
              <div class="panel-heading">
                <div>
                  <h2>待审批</h2>
                  <p>高风险写操作人工把关</p>
                </div>
                <span class="count">{{ pendingTasks.length }}</span>
              </div>
              <div v-if="!pendingTasks.length" class="empty approval-empty">当前没有待审批事项</div>
              <div v-for="task in pendingTasks.slice(0, 4)" :key="task.id" class="approval-item">
                <span class="approval-icon">✓</span>
                <div>
                  <b>{{ task.request.user_query }}</b
                  ><small>审批快照将在通过时锁定</small>
                </div>
              </div>
            </article>
          </section>

          <section class="dashboard-grid lower-grid">
            <article class="panel evidence-panel">
              <div class="panel-heading">
                <div>
                  <h2>核心 Agent 编排</h2>
                  <p>一期保持最小责任边界</p>
                </div>
              </div>
              <div class="flow">
                <span>Supervisor</span><i>→</i><span>4 个业务 Agent</span><i>→</i><span>Judge</span
                ><i>→</i><span>完成 / 审批</span>
              </div>
              <div class="legend">
                <b>A</b>业务事实 <b>B</b>检索证据 <b>C</b>模型推断 <b>D</b>缺失/未知
              </div>
            </article>
            <article class="panel">
              <div class="panel-heading">
                <div>
                  <h2>经营预警</h2>
                  <p>事实与建议分开呈现</p>
                </div>
              </div>
              <div v-for="alert in overview?.alerts" :key="alert.title" class="alert-item">
                <i :class="alert.severity"></i>
                <div>
                  <b>{{ alert.title }}</b>
                  <p>{{ alert.description }}</p>
                  <small>{{ alert.module }}</small>
                </div>
              </div>
            </article>
          </section>
        </template>

        <ModuleWorkspace v-else-if="!isDashboard" :module="currentModule" />
      </section>
    </main>
  </div>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}
:global(body) {
  margin: 0;
  min-width: 0;
  color: #172033;
  background: #f7f7fb;
  font-family: Inter, "Microsoft YaHei", sans-serif;
}
button {
  font: inherit;
  cursor: pointer;
}
.shell {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  display: flex;
  width: 244px;
  min-height: 100vh;
  flex-direction: column;
  padding: 24px 14px 18px;
  color: #cbd5e1;
  background: linear-gradient(180deg, #17122a, #251744);
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 11px 25px;
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}
.brand-mark {
  display: grid;
  width: 31px;
  height: 31px;
  color: #fff;
  background: linear-gradient(135deg, #8b5cf6, #ec4899);
  border-radius: 9px;
  place-items: center;
}
.shop-switcher {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  color: #fff;
  background: #ffffff0d;
  border: 1px solid #ffffff17;
  border-radius: 10px;
}
.shop-switcher span:nth-child(2) {
  flex: 1;
}
.shop-switcher b,
.shop-switcher small {
  display: block;
}
.shop-switcher b {
  font-size: 12px;
}
.shop-switcher small {
  margin-top: 4px;
  color: #9ca3af;
  font-size: 10px;
}
.shop-switcher select {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  cursor: pointer;
}
.shop-icon {
  display: grid;
  width: 28px;
  height: 28px;
  background: #8b5cf633;
  border-radius: 7px;
  place-items: center;
  font-size: 11px;
}
nav {
  margin-top: 22px;
}
.nav-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  color: #b8b5c9;
  background: transparent;
  border: 0;
  border-radius: 8px;
  text-align: left;
  font-size: 13px;
}
.nav-item:hover,
.nav-item.active {
  color: #fff;
  background: #ffffff12;
}
.nav-item.active {
  box-shadow: inset 3px 0 #a78bfa;
}
.nav-dot {
  width: 6px;
  height: 6px;
  background: #6b7280;
  border-radius: 50%;
}
.nav-item.active .nav-dot {
  background: #c4b5fd;
  box-shadow: 0 0 10px #a78bfa;
}
.sidebar-note {
  margin-top: auto;
  padding: 15px 12px;
  border-top: 1px solid #ffffff14;
}
.sidebar-note span,
.sidebar-note b,
.sidebar-note small {
  display: block;
}
.sidebar-note span {
  color: #a78bfa;
  font-size: 10px;
  letter-spacing: 1px;
}
.sidebar-note b {
  margin-top: 5px;
  color: #fff;
  font-size: 13px;
}
.sidebar-note small {
  margin-top: 5px;
  color: #8f8aa1;
  font-size: 10px;
  line-height: 1.5;
}
.workspace {
  flex: 1;
}
.topbar {
  display: flex;
  height: 62px;
  align-items: center;
  justify-content: space-between;
  padding: 0 35px;
  background: #fff;
  border-bottom: 1px solid #e7e5ec;
  color: #7b8495;
  font-size: 12px;
}
.topbar b {
  color: #364153;
}
.environment {
  padding: 4px 7px;
  margin-right: 16px;
  color: #6d28d9;
  background: #f3e8ff;
  border-radius: 10px;
  font-size: 9px;
  font-weight: 800;
}
.user {
  color: #4b5563;
}
.content {
  max-width: 1450px;
  padding: 31px 38px 44px;
  margin: 0 auto;
}
.page-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin-bottom: 24px;
}
.eyebrow {
  margin: 0 0 7px;
  color: #7c3aed;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 1.7px;
}
.page-heading h1 {
  margin: 0;
  font-size: 28px;
}
.page-heading p:not(.eyebrow) {
  margin: 8px 0 0;
  color: #7b8495;
  font-size: 12px;
}
.heading-actions {
  display: flex;
  gap: 10px;
}
.primary,
.secondary {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
}
.primary {
  color: #fff;
  background: linear-gradient(135deg, #7c3aed, #9333ea);
  border: 1px solid #7c3aed;
}
.secondary {
  color: #475569;
  background: #fff;
  border: 1px solid #dfe3ea;
}
button:disabled {
  opacity: 0.55;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 16px;
}
.metric-grid.muted {
  opacity: 0.55;
}
.metric-card,
.panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 3px 12px #1f29370a;
}
.metric-card {
  padding: 18px 19px;
}
.metric-card > span {
  color: #64748b;
  font-size: 12px;
}
.metric-card strong {
  display: block;
  margin: 11px 0 6px;
  font-size: 26px;
}
.metric-card small {
  font-size: 11px;
  font-weight: 650;
}
.up {
  color: #059669;
}
.down {
  color: #dc4b5d;
}
.flat {
  color: #d97706;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1.65fr 1fr;
  gap: 16px;
}
.lower-grid {
  margin-top: 16px;
  grid-template-columns: 1.35fr 1fr;
}
.panel {
  padding: 20px;
}
.panel-heading {
  display: flex;
  align-items: start;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel h2 {
  margin: 0;
  font-size: 15px;
}
.panel-heading p {
  margin: 5px 0 0;
  color: #8490a1;
  font-size: 11px;
}
.link-button {
  color: #7c3aed;
  background: transparent;
  border: 0;
  font-size: 11px;
  font-weight: 700;
}
.table-head,
.task-row {
  display: grid;
  grid-template-columns: 2.4fr 1fr 0.8fr;
  gap: 12px;
  align-items: center;
}
.table-head {
  padding: 8px 10px;
  color: #8a95a5;
  background: #faf9fc;
  font-size: 10px;
}
.task-row {
  padding: 13px 10px;
  color: #596579;
  border-bottom: 1px solid #f0edf4;
  font-size: 11px;
}
.task-row b {
  display: block;
  overflow: hidden;
  color: #303b4d;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}
.task-row small {
  display: block;
  margin-top: 4px;
  color: #9aa3b1;
  font-size: 9px;
}
.status {
  display: inline-flex;
  width: fit-content;
  padding: 4px 8px;
  color: #6d28d9;
  background: #f3e8ff;
  border-radius: 12px;
  font-weight: 700;
}
.status.completed {
  color: #047857;
  background: #ecfdf5;
}
.status.failed,
.status.cancelled {
  color: #be123c;
  background: #fff1f2;
}
.count {
  display: grid;
  width: 29px;
  height: 29px;
  color: #7c3aed;
  background: #f3e8ff;
  border-radius: 9px;
  place-items: center;
  font-weight: 800;
}
.empty {
  padding: 35px 10px;
  color: #929cab;
  text-align: center;
  font-size: 12px;
}
.approval-empty {
  padding-top: 53px;
}
.approval-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 13px 0;
  border-bottom: 1px solid #f0edf4;
}
.approval-icon {
  display: grid;
  width: 29px;
  height: 29px;
  color: #7c3aed;
  background: #f3e8ff;
  border-radius: 8px;
  place-items: center;
}
.approval-item b,
.approval-item small {
  display: block;
}
.approval-item b {
  font-size: 11px;
}
.approval-item small {
  margin-top: 4px;
  color: #929cab;
  font-size: 9px;
}
.flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 9px;
  padding: 18px;
  background: linear-gradient(90deg, #faf5ff, #fdf2f8);
  border-radius: 10px;
}
.flow span {
  padding: 8px 10px;
  color: #53328e;
  background: #fff;
  border: 1px solid #e9d5ff;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  text-align: center;
}
.flow i {
  color: #a78bfa;
  font-style: normal;
}
.legend {
  margin-top: 14px;
  color: #7b8495;
  font-size: 10px;
  word-spacing: 7px;
}
.legend b {
  display: inline-grid;
  width: 18px;
  height: 18px;
  color: #fff;
  background: #7c3aed;
  border-radius: 5px;
  place-items: center;
  font-size: 9px;
}
.alert-item {
  display: flex;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f0edf4;
}
.alert-item > i {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
  background: #f59e0b;
}
.alert-item > i.high {
  background: #ef476f;
}
.alert-item b {
  font-size: 11px;
}
.alert-item p {
  margin: 5px 0;
  color: #748094;
  font-size: 10px;
  line-height: 1.5;
}
.alert-item small {
  color: #9ba4b2;
  font-size: 9px;
}
.error-state {
  display: flex;
  justify-content: space-between;
  padding: 14px 17px;
  margin-bottom: 16px;
  color: #a32642;
  background: #fff1f4;
  border: 1px solid #ffd7e0;
  border-radius: 9px;
  font-size: 12px;
}
.error-state button {
  color: inherit;
  background: transparent;
  border: 0;
  text-decoration: underline;
}
@media (max-width: 1200px) {
  .sidebar {
    width: 216px;
  }
  .content {
    padding: 27px 24px 38px;
  }
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dashboard-grid,
  .lower-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .flow {
    justify-content: flex-start;
  }
}
</style>
