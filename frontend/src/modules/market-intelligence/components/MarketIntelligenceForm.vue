<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type {
  DataSourceOption,
  MarketIntelligenceRequest,
  ProfitCalculatorParameters,
  TaskPreviewResponse,
} from "../types/marketIntelligence";

const props = defineProps<{
  query: string;
  preview: TaskPreviewResponse | null;
  draft: MarketIntelligenceRequest | null;
  previewing: boolean;
  submitting: boolean;
  fieldError: string;
}>();
const emit = defineEmits<{
  "update:query": [value: string];
  preview: [];
  submit: [value: MarketIntelligenceRequest];
}>();

const editable = ref<MarketIntelligenceRequest | null>(null);
const profitEnabled = ref(false);

function cloneRequest(value: MarketIntelligenceRequest): MarketIntelligenceRequest {
  return JSON.parse(JSON.stringify(value)) as MarketIntelligenceRequest;
}

watch(
  () => props.draft,
  (value) => {
    editable.value = value ? cloneRequest(value) : null;
    profitEnabled.value = Boolean(value?.profit_constraints);
  },
  { immediate: true },
);

const sourceOptions = computed(() => props.preview?.data_source_options ?? []);
const selectedSource = computed(() => {
  if (!editable.value) return null;
  return sourceOptions.value.find(
    (item) =>
      item.platform.toLowerCase() === editable.value?.platforms[0]?.toLowerCase() &&
      item.market.toLowerCase() === editable.value?.market.toLowerCase() &&
      item.data_source_mode === editable.value?.data_source_mode,
  ) ?? null;
});
const selectedSourceKey = computed({
  get: () => selectedSource.value ? sourceKey(selectedSource.value) : "",
  set: (value: string) => {
    if (!editable.value) return;
    const option = sourceOptions.value.find((item) => sourceKey(item) === value);
    if (!option || !option.available) return;
    editable.value.platforms = [option.platform];
    editable.value.market = option.market;
    editable.value.data_source_mode = option.data_source_mode;
  },
});
const canSubmit = computed(
  () =>
    Boolean(editable.value && selectedSource.value?.available) &&
    !props.preview?.missing_fields.length &&
    !props.submitting,
);

function sourceKey(option: DataSourceOption) {
  return `${option.platform}|${option.market}|${option.data_source_mode}`;
}

function sourceCapabilities(option: DataSourceOption) {
  const capabilities = [
    option.supports_products && "商品",
    option.supports_reviews && "评论",
    option.supports_market_metrics && "市场指标",
  ].filter(Boolean);
  return capabilities.length ? `支持：${capabilities.join("、")}` : option.unavailable_reason;
}

function defaultProfit(): ProfitCalculatorParameters {
  return {
    schema_version: "1.0",
    price: "49.99",
    product_cost: "18",
    platform_fee: "7.5",
    logistics_cost: "6",
    advertising_cost: "5",
    minimum_margin: "0.30",
    currency: "USD",
  };
}

function toggleProfit() {
  if (!editable.value) return;
  editable.value.profit_constraints = profitEnabled.value ? defaultProfit() : null;
}

function submit() {
  if (editable.value && canSubmit.value) emit("submit", cloneRequest(editable.value));
}

function invalid(field: string) {
  return props.fieldError === field || props.fieldError.endsWith(`.${field}`);
}
</script>

<template>
  <section class="analysis-card" aria-labelledby="analysis-title">
    <div class="section-heading">
      <div>
        <span class="eyebrow">01 · 定义机会</span>
        <h2 id="analysis-title">告诉 Agent 你想分析什么</h2>
      </div>
      <span class="dataset-pill">可选择数据来源</span>
    </div>

    <label class="field-label" for="market-query">商品与分析目标</label>
    <textarea
      id="market-query"
      class="query-input"
      :value="query"
      rows="4"
      placeholder="例如：分析便携咖啡机在美国亚马逊是否值得进入，目标毛利率至少 30%"
      :disabled="previewing || submitting"
      @input="emit('update:query', ($event.target as HTMLTextAreaElement).value)"
    ></textarea>
    <div class="query-footer">
      <span>支持中英文商品别名，先预解析再提交正式任务</span>
      <button
        class="primary-action"
        type="button"
        :disabled="query.trim().length < 5 || previewing || submitting"
        @click="emit('preview')"
      >
        {{ previewing ? "正在理解需求…" : preview ? "重新预解析" : "预解析需求" }}
      </button>
    </div>

    <template v-if="preview">
      <div class="preview-summary">
        <div>
          <span class="summary-label">识别置信度</span>
          <strong>{{ Math.round(preview.confidence * 100) }}%</strong>
        </div>
        <div>
          <span class="summary-label">数据可用性</span>
          <strong :class="selectedSource?.available ? 'text-success' : 'text-danger'">
            {{ selectedSource?.available ? "可分析" : "暂不可用" }}
          </strong>
        </div>
      </div>

      <div v-if="preview.missing_fields.length" class="notice danger" role="alert">
        <strong>还缺少必要信息</strong>
        <span>{{ preview.missing_fields.join("、") }}</span>
      </div>
      <div v-if="preview.ambiguities.length" class="notice warning" role="alert">
        <strong>需要确认</strong>
        <span>{{ preview.ambiguities.join("；") }}</span>
      </div>
      <div
        v-for="warning in preview.warnings"
        :key="`${warning.code}-${warning.field}`"
        class="notice"
        :class="warning.severity"
        role="status"
      >
        <strong>{{ warning.code }}</strong><span>{{ warning.message }}</span>
      </div>

      <div v-if="editable" class="confirmation-panel">
        <div class="confirmation-title">
          <div>
            <span class="eyebrow">02 · 确认参数</span>
            <h3>检查 Agent 提取结果</h3>
          </div>
          <span>提交前可以直接修改</span>
        </div>

        <div class="form-grid">
          <label :class="{ invalid: invalid('market') }">
            <span>目标市场</span>
            <input v-model.trim="editable.market" type="text" />
          </label>
          <label
            class="source-selector"
            :class="{ invalid: invalid('platforms') || invalid('data_source_mode') }"
          >
            <span>分析平台与数据来源</span>
            <select v-model="selectedSourceKey">
              <option
                v-for="option in sourceOptions"
                :key="sourceKey(option)"
                :value="sourceKey(option)"
                :disabled="!option.available"
              >
                {{ option.label }}{{ option.available ? "" : `（${option.unavailable_reason}）` }}
              </option>
            </select>
            <small v-if="selectedSource">{{ sourceCapabilities(selectedSource) }}</small>
          </label>
          <label :class="{ invalid: invalid('category') }">
            <span>商品类目</span>
            <input v-model.trim="editable.category" type="text" />
          </label>
          <label :class="{ invalid: invalid('keyword') }">
            <span>关键词</span>
            <input v-model.trim="editable.keyword" type="text" />
          </label>
          <label :class="{ invalid: invalid('collection.product_limit') }">
            <span>商品数量</span>
            <input v-model.number="editable.collection.product_limit" min="1" max="50" type="number" />
          </label>
          <label :class="{ invalid: invalid('collection.review_limit_per_product') }">
            <span>每件商品评论数</span>
            <input
              v-model.number="editable.collection.review_limit_per_product"
              min="1"
              type="number"
            />
          </label>
        </div>

        <label class="profit-toggle">
          <input v-model="profitEnabled" type="checkbox" @change="toggleProfit" />
          <span>
            <strong>同时测算利润可行性</strong>
            <small>不填写成本时仍会分析市场，报告会标记利润数据受限</small>
          </span>
        </label>

        <div v-if="profitEnabled && editable.profit_constraints" class="form-grid profit-grid">
          <label>
            <span>销售价格</span>
            <input v-model.trim="editable.profit_constraints.price" inputmode="decimal" />
          </label>
          <label>
            <span>商品成本</span>
            <input v-model.trim="editable.profit_constraints.product_cost" inputmode="decimal" />
          </label>
          <label>
            <span>平台费用</span>
            <input v-model.trim="editable.profit_constraints.platform_fee" inputmode="decimal" />
          </label>
          <label>
            <span>物流成本</span>
            <input v-model.trim="editable.profit_constraints.logistics_cost" inputmode="decimal" />
          </label>
          <label>
            <span>广告成本</span>
            <input v-model.trim="editable.profit_constraints.advertising_cost" inputmode="decimal" />
          </label>
          <label>
            <span>最低毛利率</span>
            <input v-model.trim="editable.profit_constraints.minimum_margin" inputmode="decimal" />
          </label>
        </div>

        <div class="submit-row">
          <p v-if="!selectedSource?.available">
            当前没有可执行的数据来源，请选择已接入并获得授权的平台。
          </p>
          <p v-else>将使用 {{ selectedSource.label }}，提交后由 Worker 执行。</p>
          <button class="submit-action" type="button" :disabled="!canSubmit" @click="submit">
            {{ submitting ? "正在创建任务…" : "确认并开始分析" }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.analysis-card {
  padding: clamp(1.25rem, 2.5vw, 2rem);
  background: var(--cui-body-bg);
  border: 1px solid var(--cui-border-color);
  border-radius: 18px;
  box-shadow: 0 16px 40px rgb(25 36 61 / 7%);
}
.section-heading,
.confirmation-title,
.query-footer,
.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.eyebrow {
  color: #5d6b82;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
h2 { margin: 0.35rem 0 1.5rem; font-size: clamp(1.35rem, 3vw, 1.8rem); }
h3 { margin: 0.25rem 0 0; font-size: 1.1rem; }
.dataset-pill {
  padding: 0.4rem 0.75rem;
  color: #285944;
  background: #e8f4ee;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}
.field-label { display: block; margin-bottom: 0.5rem; font-weight: 700; }
.query-input {
  width: 100%;
  padding: 1rem;
  resize: vertical;
  color: var(--cui-body-color);
  background: var(--cui-tertiary-bg);
  border: 1px solid var(--cui-border-color);
  border-radius: 12px;
  line-height: 1.65;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.query-input:focus,
input:focus,
select:focus { border-color: #4f6bed; box-shadow: 0 0 0 3px rgb(79 107 237 / 14%); outline: 0; }
.query-footer { margin-top: 0.8rem; color: var(--cui-secondary-color); font-size: 0.78rem; }
.primary-action,
.submit-action {
  flex: 0 0 auto;
  padding: 0.72rem 1.15rem;
  color: white;
  background: #334bc4;
  border: 0;
  border-radius: 10px;
  font-weight: 750;
}
button:disabled { cursor: not-allowed; opacity: 0.55; }
.preview-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin-top: 1.5rem;
  overflow: hidden;
  background: var(--cui-border-color);
  border: 1px solid var(--cui-border-color);
  border-radius: 12px;
}
.preview-summary > div { display: flex; min-width: 0; padding: 0.9rem 1rem; background: var(--cui-body-bg); flex-direction: column; }
.summary-label { color: var(--cui-secondary-color); font-size: 0.72rem; }
.preview-summary strong { margin-top: 0.15rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notice { display: flex; gap: 0.8rem; margin-top: 0.75rem; padding: 0.8rem 1rem; color: #24536a; background: #edf6fa; border-radius: 10px; font-size: 0.83rem; }
.notice.warning { color: #70571a; background: #fff6db; }
.notice.danger { color: #7c3131; background: #fcebea; }
.confirmation-panel { margin-top: 1.6rem; padding-top: 1.5rem; border-top: 1px solid var(--cui-border-color); }
.confirmation-title > span { color: var(--cui-secondary-color); font-size: 0.78rem; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 1.2rem; }
.form-grid label { display: flex; gap: 0.4rem; flex-direction: column; font-size: 0.78rem; font-weight: 700; }
.form-grid input,
.form-grid select { width: 100%; min-height: 42px; padding: 0.55rem 0.7rem; color: var(--cui-body-color); background: var(--cui-body-bg); border: 1px solid var(--cui-border-color); border-radius: 9px; }
.form-grid input:disabled { background: var(--cui-tertiary-bg); }
.form-grid label.invalid > span { color: #a33f48; }
.form-grid label.invalid input,
.form-grid label.invalid select { border-color: #c95862; box-shadow: 0 0 0 3px rgb(201 88 98 / 10%); }
.source-selector small { color: var(--cui-secondary-color); font-weight: 500; line-height: 1.45; }
.profit-toggle { display: flex; align-items: flex-start; gap: 0.75rem; margin-top: 1.3rem; padding: 1rem; cursor: pointer; background: var(--cui-tertiary-bg); border-radius: 12px; }
.profit-toggle input { width: 1.05rem; height: 1.05rem; margin-top: 0.2rem; accent-color: #334bc4; }
.profit-toggle span { display: flex; flex-direction: column; }
.profit-toggle small { margin-top: 0.2rem; color: var(--cui-secondary-color); }
.profit-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.submit-row { margin-top: 1.5rem; }
.submit-row p { margin: 0; color: var(--cui-secondary-color); font-size: 0.8rem; }
.submit-action { padding-inline: 1.4rem; background: #18233f; }
@media (max-width: 767px) {
  .preview-summary,
  .form-grid,
  .profit-grid { grid-template-columns: 1fr; }
  .section-heading,
  .confirmation-title,
  .query-footer,
  .submit-row { align-items: stretch; flex-direction: column; }
  .primary-action,
  .submit-action { width: 100%; }
}
</style>
