# Codex Execution Guard 使用手册

[English](USAGE.en.md)

README 负责快速判断，本文说明一次任务如何从规划进入执行、每一步会检查什么，以及出现问题时怎样处理。

## 1. 使用前提

- 支持插件和 Hooks 的当前 Codex CLI 或 ChatGPT 桌面版。
- 本机可执行的 `python3`。
- 一个 Git 仓库；新任务的隔离依赖 Codex 原生 worktree 环境。
- 对当前项目的本地写入权限。

插件运行时不需要 MCP、远程服务器、数据库、账号系统或额外 API Key。安装和更新源码需要访问 GitHub，执行状态保存在本机。

## 2. 安装

```bash
codex plugin marketplace add AKin-lvyifang/codex-execution-guard --ref main
codex plugin add codex-execution-guard@codex-execution-guard
```

如果需要检查源码或参与开发，可以改用本地 marketplace：

```bash
git clone https://github.com/AKin-lvyifang/codex-execution-guard.git
cd codex-execution-guard
codex plugin marketplace add "$(pwd)"
codex plugin add codex-execution-guard@codex-execution-guard
```

也可以在 `/plugins` 中找到 **Codex Execution Guard** 并安装。桌面版添加或更新本地 marketplace 后，请重启应用并新建任务；旧任务不会可靠地热加载新的 Skill 与 Hook 定义。

打开 `/hooks`，阅读并信任当前版本。Execution Guard 使用 `UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PreCompact`、`SessionStart` 和 `Stop`。Hook 定义变化后，Codex 可能要求重新信任。

## 3. 配置触发规则

推荐把下面规则放进全局或项目 `AGENTS.md`：

```text
当用户明确要求开始实施新功能、独立代码任务或继续既有功能时，项目主会话必须调用 $execution-guard；任务创建或复用、模型与思考强度选择、worktree 与分支管理、计划固化、执行恢复和结果收口全部以该 Skill 为准。未经用户明确授权，不得 push、创建 PR、运行远程 CI、Tag、Release 或部署。
```

这条规则只负责路由。任务归属、模型路由、合同格式、恢复和停止条件都留在插件里，避免全局提示词不断变长。

如果不修改 `AGENTS.md`，每次确认执行时明确发送：

```text
方案确认，开始执行，使用 $execution-guard。
```

## 4. 先在主会话规划

主会话负责产品判断和最终决定。开始前至少确认：

- 用户要看到的结果。
- 允许修改的仓库、模块或路径。
- 已确认决定和明确非目标。
- 有稳定编号的计划步骤。
- 可观察的验收标准。
- 允许使用的模型与思考强度范围。
- 允许进行的本地验证，以及禁止的远程动作。

存在产品歧义时继续在主会话讨论，不把“自己猜一个方案”交给执行任务。

## 5. 主控判断新建还是复用

| 现场 | 动作 |
| --- | --- |
| 目标、范围和验收标准不变 | 继续原任务 |
| 原功能的修复、调整、测试或文档 | 继续原任务 |
| 原迭代已经关闭或合并 | 创建新任务 |
| 出现独立用户价值 | 创建新任务 |
| 出现新的验收标准 | 创建新任务 |
| 证据缺失或互相矛盾 | 停在主控决定 |

本地所有权记录保存迭代对应的真实任务、worktree、分支和基线。它位于明确选择的私有本地状态路径，不会提交进仓库。

## 6. 选择执行模型

主控优先读取宿主当前公开的模型与思考强度组合，再与用户授权池求交集。插件自带的路由表只是选择政策，不是实时可用模型清单。

| 任务形态 | 建议执行档位 |
| --- | --- |
| 清楚、机械、范围很小 | Luna Max |
| 普通功能或边界明确的修复 | Terra Max |
| 决策已经冻结的跨模块实现 | Sol High |
| 产品方向仍有歧义 | 留在 Sol Ultra 主控继续规划 |
| 一次高风险终审 | 最多一次 Sol XHigh 或 Ultra |

宿主没有实时发现能力时，只能在用户允许的本地授权池中回退，并明确写出“非实时发现”。创建任务接受某个模型请求，也不等于宿主已经证明实际运行模型；没有运行时元数据时必须写 `actual model unverified`。

## 7. 创建并核对 worktree 任务

新迭代按以下顺序启动：

1. 通过 Codex 原生项目工具找到真实 Git 项目。
2. 创建一个左侧可见、环境类型为 worktree 的任务。
3. 把 `clientThreadId` 只当成排队标识，等待真实 `threadId`。
4. 设置清楚的任务标题。
5. 让新任务只报告 `cwd`、worktree 身份、分支、完整 `HEAD` 和 Git 状态。
6. 若任务处于 detached HEAD，只建立并切换一条唯一的 `codex/<iteration>` 分支。
7. 要求干净现场，除非合同明确允许基线改动。
8. 主控验证并保存真实基线后，才发送执行合同。

用于取得环境身份的第一次提示不带激活标记，也不允许写代码、登记计划、验证、提交或再创建任务。

## 8. 执行合同

Execution Guard 使用单独一行的版本化标记激活受控执行：

```text
CODEX_EXECUTION_GUARD_CONTRACT_V1
```

标记后是一份 JSON 合同，包含合同版本和稳定 ID、目标、范围、决定、非目标、禁止操作、授权模型、真实 Git 基线、稳定计划、允许调整、升级条件、验证预算和验收标准。

普通会话没有收到合法标记时，Hooks 保持无状态并成功退出，不应影响日常聊天。

## 9. 写代码前登记计划

执行会话收到合同后：

1. 核对 `pwd`、worktree、分支、`HEAD` 和 Git 状态。
2. 与合同基线比较，不一致就停止写入。
3. 把合同中的完整计划原样发送给 `update_plan`。
4. 保留全部步骤、顺序和稳定编号，同时最多只有一步 `in_progress`。

执行会话只能改变步骤状态和不影响范围、授权或验收的简短实现说明。删除、改写、重排或增加步骤需要回到主控。

## 10. 开发时怎样避免打转

一项新工作只有满足以下任一条件，才能进入当前实现：

- 它就是当前交付物。
- 已经观察到真实失败。
- 它属于已批准验收标准。
- 它直接阻止下一步继续。

未来加固、理论风险、可选能力、额外哈希、指纹或通用门禁只记录为待办。相同命令、结果、Git 状态、当前步骤和验收目标没有变化时，重复运行不会被记成新进展。

需要新步骤、扩大范围、改变验收、使用未授权模型或执行禁止操作时，执行会话登记证据并返回主控，不自行改合同。

## 11. 上下文压缩与恢复

压缩前，Hooks 保存已经结构化的状态。恢复或重新进入后，只注入继续执行所需的信息：合同 ID 和目标、模型路由、范围、决定、非目标、禁止操作、当前步骤、完整计划与验收状态、Git 身份、允许偏差和简短证据。

恢复后会再次核对 Git 现场。插件不依赖已经失真的聊天摘要重新猜任务，也不会重放完整规划记录。

## 12. 完成与收据

仍有计划或验收项未完成，并且没有登记证据充分的升级时，`Stop` Hook 会要求继续。完成后交回：

- 合同 ID。
- 已完成计划和验收 ID。
- 修改路径与本地提交。
- 每种状态下只记录一次的验证命令和结果。
- 允许偏差及原因。
- 未验证项或真实阻塞。
- 远程与发布动作状态。

最终验收、合并本地 `main` 和任何远程发布决定留在主控。

## 13. 更新插件

```bash
codex plugin marketplace upgrade codex-execution-guard
codex plugin add codex-execution-guard@codex-execution-guard
```

如果使用的是本地克隆仓库，先在仓库中运行 `git pull --ff-only`，再重新安装插件。随后重启桌面应用，重新检查发生变化的 Hooks，并在新任务中验证。不要用正在运行的旧任务判断新版本是否已经加载。

## 14. 常见问题

### `/plugins` 中看不到插件

确认 marketplace 添加命令使用的是仓库根目录，根目录下应同时存在 `.agents/plugins/marketplace.json` 和 `plugins/codex-execution-guard/`。运行 `codex plugin list`，重启桌面应用并新建任务。

### 插件已安装，但 Hooks 没有生效

检查 `/hooks` 中是否出现当前定义、是否已经信任，以及任务是否在安装或更新后新建。普通会话没有合同标记时保持无动作是正确行为。

### 执行会话一直不允许写入

核对合同里的绝对 worktree、分支和完整 `HEAD` 是否与现场一致，并确认完整计划已经原样登记。基线不一致时回主控重新确认，不要绕过 Hook。

### 只拿到了 `clientThreadId`

任务仍在排队。继续等待宿主返回真实 `threadId` 和工作环境，不能发送受控合同或开始实现。

### 实际模型无法核对

宿主没有返回运行时模型身份。保留“已请求的模型”和 `actual model unverified` 两个事实，不把请求成功写成实际运行已验证。

### 测试全过，宿主里仍然没有生效

单元测试验证固定载荷与本地状态机；marketplace 重载、Skill 发现、Hook 信任和宿主工具能力属于真实环境验收，需要重启后在新任务中检查。
