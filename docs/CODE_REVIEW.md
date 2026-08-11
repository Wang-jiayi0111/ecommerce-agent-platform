# 代码查验与规范

每次代码提交均通过本地检查与 GitHub Pull Request 检查。`main` 分支只接受通过 CI 并完成审查的 Pull Request。

## 开发者提交步骤

```powershell
# 首次安装依赖
cd backend; python -m pip install -e ".[dev]"
cd ../frontend; npm.cmd install

# 每次提交前
cd ..
.\scripts\Verify-Code.ps1
git add .
git commit -m "feat(scope): 简短说明"
git push -u origin HEAD
```

## 自动质量门禁

| 范围 | 工具 | 阻断条件 |
| --- | --- | --- |
| 后端静态检查 | Ruff | 未使用导入、导入排序、基础缺陷、过时写法 |
| 后端格式 | Ruff Format | 格式与仓库规则不一致 |
| 后端行为 | Pytest | 单元或接口测试失败 |
| 前端静态检查 | ESLint | Vue、TypeScript 或 JavaScript 规则错误 |
| 前端格式 | Prettier | 文件格式不符合规则 |
| 前端构建 | Vue TSC + Vite | 类型错误或构建失败 |
| API 契约 | FastAPI OpenAPI | OpenAPI 生成失败或路由契约缺失 |

## GitHub 必须配置

在仓库 `Settings -> Branches -> Add branch protection rule` 中为 `main` 启用：

1. Require a pull request before merging。
2. Require approvals（至少 1 人）。
3. Require status checks to pass before merging，选择 `backend` 与 `frontend`。
4. Require branches to be up to date before merging。
5. Block force pushes 与 deletion。

代码审查重点：功能是否有测试、外部写操作是否经过审批、是否出现密钥或真实个人数据、是否跨越模块边界、异常路径是否可恢复、日志是否脱敏。
