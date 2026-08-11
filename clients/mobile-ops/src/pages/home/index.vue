<script setup lang="ts">
const metrics = [
  { label: "今日 GMV", value: "¥128,640" },
  { label: "转化率", value: "3.86%" },
  { label: "库存风险", value: "12" },
];
</script>

<template>
  <view class="page">
    <view class="header"><text class="eyebrow">COMMERCE AGENT</text><text class="title">今日经营</text><text class="subtitle">Amazon US 演示店 · 数据截止 08:30</text></view>
    <view class="metric-grid"><view v-for="metric in metrics" :key="metric.label" class="metric-card"><text>{{ metric.label }}</text><strong>{{ metric.value }}</strong></view></view>
    <view class="section"><view class="section-title"><text>待处理事项</text><navigator url="/pages/tasks/index">全部 →</navigator></view><view class="empty">当前没有待审批事项</view></view>
  </view>
</template>

<style scoped>
.page { padding: 32rpx; }.header { display: flex; flex-direction: column; gap: 10rpx; }.eyebrow { color: #7c3aed; font-size: 22rpx; font-weight: 700; letter-spacing: 2rpx; }.title { font-size: 48rpx; font-weight: 700; }.subtitle { color: #77859d; font-size: 25rpx; }.metric-grid { display: flex; gap: 18rpx; margin: 34rpx 0; }.metric-card { flex: 1; display: flex; flex-direction: column; gap: 16rpx; padding: 24rpx; background: #fff; border-radius: 16rpx; color: #748198; font-size: 24rpx; }.metric-card strong { color: #15233e; font-size: 31rpx; }.section { padding: 28rpx; background: #fff; border-radius: 16rpx; }.section-title { display: flex; justify-content: space-between; font-weight: 700; }.section-title navigator { color: #7c3aed; font-size: 25rpx; }.empty { padding: 48rpx 0 20rpx; color: #8d99aa; text-align: center; font-size: 26rpx; }
</style>
