# Changelog / 变更记录

All notable changes to this project are documented here. 本文件记录项目的重要变化。

## Unreleased / 未发布

- No changes yet. / 暂无变更。

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
