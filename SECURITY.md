# Security Policy / 安全政策

## Supported versions / 支持版本

| Version | Supported |
| --- | --- |
| `0.2.x` | Yes |
| `< 0.2` | No |

## Report a vulnerability / 报告漏洞

Please use GitHub's private vulnerability reporting or a private Security Advisory for this repository. Do not publish credentials, private paths, live execution contracts, registry contents, or sensitive logs in a public issue.

请优先使用 GitHub 私有漏洞报告或本仓库的私有 Security Advisory。不要在公开 Issue 中粘贴凭据、私有路径、实时执行合同、registry 内容或敏感日志。

Include the affected version, Codex host, Hook event or tool path, minimal reproduction steps, expected behavior, observed behavior, and whether an ordinary unmarked session is affected.

报告请包含受影响版本、Codex 宿主、相关 Hook 事件或工具路径、最小复现、预期行为、实际行为，以及普通未标记会话是否受到影响。

## Security boundary / 安全边界

Execution Guard is a workflow guardrail, not a sandbox or a complete security boundary. Host tool paths may exist outside Hook coverage. The plugin does not claim to prevent a malicious process, compromised host, or direct filesystem access.

Execution Guard 是工作流护栏，不是沙箱或完整安全边界。宿主可能存在 Hooks 无法覆盖的工具路径；插件不承诺阻止恶意进程、已被入侵的宿主或直接文件系统访问。

The runtime has no MCP server, hosted service, telemetry, or required network call. State is stored locally, and remote Git or publishing actions require explicit user authorization.

运行时没有 MCP server、托管服务、遥测或必要网络请求。状态保存在本机，远程 Git 与发布动作必须获得用户明确授权。
