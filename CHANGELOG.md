# Changelog / 变更记录

All notable changes to this project are documented here. 本文件记录项目的重要变化。

## Unreleased / 未发布

- Added locked V2 creation claims, reconcile-only recovery, atomic finalization, and migration of V1 ownership records on the next locked write. / 增加持锁的 V2 创建 claim、仅 reconcile 恢复、原子 finalize，以及下一次持锁写入时的 V1 所有权记录迁移。
- Prevented automatic duplicate task creation after queue state, errors, timeouts, crashes, or reloads; zero or multiple native candidates now stop without retry or automatic archive. / 防止排队、报错、超时、崩溃或重载后自动重复创建任务；原生候选为零个或多个时停止，不重试也不自动归档。
- Replaced the default visible JSON handoff with a UTF-8-bounded single-line task goal, private canonical contract artifact, and short SHA-256 reference, with strict format, size, ID, session, ownership, and Git-baseline checks before activation. / 默认不再在聊天正文暴露完整 JSON，改为受 UTF-8 字节上限约束的单行任务目标、私有 canonical 合同 artifact 与短 SHA-256 引用，并在激活前严格检查格式、大小、ID、session、ownership 和 Git 基线。
- Preserved inline V1 and added an explicit folded-inline cross-host fallback while rejecting reference-plus-inline ambiguity. / 保留 inline V1，并增加明确折叠的跨宿主 inline fallback，同时拒绝 reference 与 inline 并存的歧义输入。
- Removed source-level truncation from activation and compact/resume contract, plan, and acceptance context. / 移除激活与 compact/resume 上下文中对合同、计划和验收的源码级截断。

## 0.2.1 - 2026-08-10

- Fixed validation outcomes for structured `exit_code` responses while preserving text and `returncode` compatibility. / 修复结构化 `exit_code` 响应的验证结果分类，同时保留文本和 `returncode` 兼容性。
- Allowed semicolon-separated pre-plan bootstrap commands only when every non-empty segment matches the existing whitelist. / 仅当每个非空片段都匹配现有白名单时，才允许计划登记前使用分号串联启动命令。

## 0.2.0 - 2026-08-09

- Added control orchestration for task creation and reuse. / 增加主控的新建与复用任务编排。
- Added host-evidence-aware model routing. / 增加基于宿主证据的模型路由。
- Added real `threadId`, worktree, branch, `HEAD`, and clean-baseline gating. / 增加真实任务与 Git 基线门槛。
- Added a process-locked, atomically replaced local ownership registry. / 增加带进程锁和原子替换的本地所有权记录。
- Preserved versioned execution contracts, stable plans, compaction recovery, validation deduplication, and completion receipts. / 保留版本化合同、稳定计划、压缩恢复、验证去重和完成收据。
- Added adversarial concurrency and stale-baseline fixtures. / 增加并发和过期基线的对抗测试。

## 0.1.0 - 2026-08-09

- Introduced the opt-in execution contract and lifecycle Hooks. / 引入按合同激活的执行护栏与生命周期 Hooks。
- Added Git baseline checks, exact plan registration, progress evidence, compaction recovery, and stop decisions. / 增加 Git 基线检查、完整计划登记、进度证据、压缩恢复和停止判断。
