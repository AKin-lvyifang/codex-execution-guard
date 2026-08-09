# Contributing / 贡献指南

Thank you for helping improve Codex Execution Guard. 感谢你参与改进 Codex Execution Guard。

## Scope / 项目边界

The project favors the smallest sufficient mechanism for bounded Codex execution. Changes should connect to an observed failure, a documented acceptance case, a supported host behavior, or a concrete user workflow.

本项目优先使用满足受控执行所需的最简单充分机制。改动应当对应真实失败、已有验收场景、受支持的宿主行为或明确用户流程。

Please do not add generic gate frameworks, speculative hardening, hashes, fingerprints, remote services, telemetry, or project-management features without a named threat boundary and accepted use case.

没有明确威胁边界和已接受场景时，请勿增加通用门禁框架、理论加固、哈希、指纹、远程服务、遥测或项目管理能力。

## Development setup / 开发环境

The runtime uses Python 3 standard-library modules. Clone the repository and run:

运行时只依赖 Python 3 标准库。克隆仓库后运行：

```bash
python3 -m unittest discover -s tests -v
```

When available, also run the official validators:

环境中存在官方工具时，再运行：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py \
  plugins/codex-execution-guard/skills/execution-guard

python3 /path/to/plugin-creator/scripts/validate_plugin.py \
  plugins/codex-execution-guard
```

## Change rules / 修改规则

- Keep ordinary unmarked sessions inert and fail-open. / 普通未标记会话必须保持无状态且不受影响。
- Preserve the versioned contract boundary and stable plan IDs. / 保留版本化合同边界与稳定计划编号。
- Do not commit registries, live contracts, absolute personal paths, credentials, or transcripts. / 不提交 registry、实时合同、个人绝对路径、凭据或聊天记录。
- Keep remote Git and release actions outside automatic execution. / 远程 Git 与发布操作不得进入自动执行路径。
- Add or update focused fixtures for behavior changes. / 行为变化需要增加或更新聚焦测试。
- Distinguish fixture evidence from fresh-host installation and Hook-trust evidence. / 区分单元测试证据与真实宿主安装、Hook 信任证据。

## Pull requests / Pull Request

1. Describe the user or host problem. / 说明用户或宿主问题。
2. Explain why the change belongs in the current scope. / 说明为什么属于当前范围。
3. Keep the diff focused and include tests. / 保持改动聚焦并提供测试。
4. Report exact validation commands and remaining host checks. / 写明验证命令与尚需人工完成的宿主检查。
5. Confirm that no private path, credential, transcript, or registry was added. / 确认没有加入私有路径、凭据、聊天记录或状态文件。

By contributing, you agree that your contribution is licensed under the repository's MIT License.

提交贡献即表示你同意按本仓库 MIT License 授权该贡献。
