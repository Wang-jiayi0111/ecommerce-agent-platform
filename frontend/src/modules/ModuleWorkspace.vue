<script setup lang="ts">
import type { NavigationItem } from "../config/navigation";

defineProps<{ module: NavigationItem }>();
</script>

<template>
  <section class="module-workspace">
    <p class="eyebrow">BUSINESS MODULE</p>
    <h1>{{ module.label }}</h1>
    <p class="description">{{ module.description }}</p>
    <article class="module-card">
      <span class="status">领域框架已建立</span>
      <h2>按纵向能力继续交付</h2>
      <p>
        后端模块：{{ module.apiModule }}。在此领域补充 Schema、Service、Repository、
        Tool/Adapter、API、审计事件和自动化测试。
      </p>
      <a href="/docs" target="_blank" rel="noreferrer">查看 API 文档 →</a>
    </article>
  </section>
</template>

<style scoped>
.module-workspace {
  padding: 58px 0;
}
.eyebrow {
  margin: 0 0 8px;
  color: #7c3aed;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.5px;
}
h1 {
  margin: 0;
  font-size: 30px;
}
.description {
  color: #6b7280;
}
.module-card {
  max-width: 680px;
  padding: 28px;
  margin-top: 28px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 14px 36px #1118270d;
}
.module-card h2 {
  margin: 17px 0 8px;
  font-size: 18px;
}
.module-card p {
  color: #64748b;
  font-size: 14px;
  line-height: 1.8;
}
.module-card a {
  color: #7c3aed;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}
.status {
  display: inline-block;
  padding: 5px 9px;
  color: #6d28d9;
  background: #f3e8ff;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}
</style>
