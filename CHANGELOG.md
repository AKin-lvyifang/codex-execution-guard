# Changelog / 变更记录

All notable changes to this project are documented here. 本文件记录项目的重要变化。

## Unreleased / 未发布

- Added a dedicated Guard bootstrap marker and `PreToolUse` preflight for canonical `create_thread` project/worktree payloads, with precise correction guidance before host dispatch and unchanged no-retry semantics afterward; ordinary unmarked creation remains unaffected. / 新增 Guard bootstrap 独立标记与 `PreToolUse` 参数预检，在宿主调用前校验 canonical `create_thread` project/worktree 结构并给出精确修正提示，调用后的禁止重试语义保持不变；普通未标记创建不受影响。

## 0.3.1 - 2026-08-12

- Required explicit control intent plus an approved, sufficiently frozen real-repository implementation before establishing a new feature chain; research, review, and one-off prototypes no longer qualify by resemblance alone. / 建立新功能链前必须同时具备明确中控意图，以及已批准且边界充分冻结的真实仓库实施；研究、评审和一次性原型不再仅因内容相似而触发路由。
- Reused the exact active implementation lane for approved same-chain follow-ups without another Guard invocation, and allowed at most one deterministic acceptance lane when isolation is genuinely required. / 同一 active 功能链已批准的后续工作无需再次点名 Guard，直接复用精确匹配的实现现场；确需隔离时最多建立一个确定性验收现场并持续复用。

## 0.3.0 - 2026-08-11

- Added locked V2 creation claims, reconcile-only recovery, atomic finalization, and migration of V1 ownership records on the next locked write. / 增加持锁的 V2 创建 claim、仅 reconcile 恢复、原子 finalize，以及下一次持锁写入时的 V1 所有权记录迁移。
- Prevented automatic duplicate task creation after queue state, errors, timeouts, crashes, or reloads; zero or multiple native candidates now stop without retry or automatic archive. / 防止排队、报错、超时、崩溃或重载后自动重复创建任务；原生候选为零个或多个时停止，不重试也不自动归档。
- Replaced the default visible JSON handoff with a UTF-8-bounded single-line task goal, private canonical contract artifact, and short SHA-256 reference, with strict format, size, ID, session, ownership, and Git-baseline checks before activation. / 默认不再在聊天正文暴露完整 JSON，改为受 UTF-8 字节上限约束的单行任务目标、私有 canonical 合同 artifact 与短 SHA-256 引用，并在激活前严格检查格式、大小、ID、session、ownership 和 Git 基线。
- Preserved inline V1 and added an explicit folded-inline cross-host fallback while rejecting reference-plus-inline ambiguity. / 保留 inline V1，并增加明确折叠的跨宿主 inline fallback，同时拒绝 reference 与 inline 并存的歧义输入。
- Accepted strict native delegation envelopes without exposing or weakening the contract marker and binding checks. / 严格兼容原生任务的 delegation envelope，不暴露也不削弱合同 marker 与绑定校验。
- Reused deterministic implementation and optional acceptance lanes across acceptance detail, retries, optimizations, and failed-acceptance fixes; retry-specific `v2` and `v3` lanes are no longer allowed. / 验收细化、复验、优化和验收失败修复复用确定性的实现与可选验收 lane，不再允许为重试创建 `v2`、`v3` lane。
- Kept ownership active through receipts, acceptance failures, and escalations. Completed or escalated contracts remain write-locked and can continue only through a private reference that revalidates active ownership; terminal archives remain idempotent across recovery events. / 完成收据、验收失败和升级后继续保留任务归属；完成或升级合同保持写锁，只能通过重新核验 active ownership 的私有引用续接，终态归档在恢复事件之间保持幂等。
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
