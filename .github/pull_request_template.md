## What changed / 改了什么

Describe the user-visible or host-visible change. / 说明用户或宿主能观察到的变化。

## Why / 为什么改

Link the observed failure, accepted use case, or supported host behavior. / 关联真实失败、已接受场景或受支持的宿主行为。

## Scope / 范围

- Included / 包含：
- Not included / 不包含：

## Validation / 验证

List exact commands and outcomes. Separate fixture evidence from fresh-host checks. / 写明实际运行的命令和结果，并区分固定测试与真实宿主检查。

```text
command → result
```

## Host checks / 宿主检查

- [ ] Not required / 不需要
- [ ] Completed in a fresh task / 已在新任务中完成
- [ ] Still required; describe below / 仍需完成，请在下方说明

## Checklist / 检查清单

- [ ] The diff stays inside the stated scope. / 改动没有超出声明范围。
- [ ] Ordinary unmarked sessions remain inert and fail-open. / 普通未标记会话仍保持无状态且不受影响。
- [ ] Stable contract, plan, baseline, and receipt boundaries remain accurate. / 合同、计划、基线和收据边界仍然准确。
- [ ] Tests or focused fixtures cover behavior changes. / 行为变化有相应测试或聚焦用例。
- [ ] No credential, personal path, live contract, registry, transcript, or private code is included. / 未包含凭据、个人路径、实时合同、registry、聊天记录或私有代码。
- [ ] Remote Git, CI, Tag, Release, and deployment remain explicitly authorized operations. / 远程 Git、CI、Tag、Release 与部署仍需明确授权。
