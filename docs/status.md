# MedDeepScientist 当前状态

## 当前定位

- 仓库角色：`MedAutoScience` 的受控 runtime 分支
- 当前开发口径：收紧 runtime protocol、收窄 adapter 依赖、谨慎吸收 upstream
- OMX 状态：已退场，仅允许历史残留

## 当前主线

- 稳定协议入口：`docs/policies/runtime_protocol.md`
- 核心工作方式入口：根 `AGENTS.md`
- 当前文档骨架：`project / architecture / invariants / decisions / status`

## 当前优先事项

1. 保持 `MedAutoScience -> MedDeepScientist` 兼容性清晰且可验证。
2. 减少 quest layout、prompt/skill、daemon API 上的隐式耦合。
3. 让 upstream intake 继续通过审计与验证推进，而不是零散吸收。

## 默认验证

- 默认最小验证：`scripts/verify.sh`
- full 验证：`scripts/verify.sh full`
- 发布相关改动：`scripts/verify.sh release`

## 补充材料

- 上游 intake 说明：`docs/upstream_intake.md`
- baseline / 审计说明：`docs/medical_fork_baseline.md`
- 公开用户文档：`docs/en/`、`docs/zh/`
