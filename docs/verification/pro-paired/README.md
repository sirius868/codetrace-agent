# DeepSeek Pro 成对真实评测

本目录保存 `deepseek-v4-pro-0813` 经 DashScope 兼容接口执行的独立评测。
配置密钥不属于报告；Qwen、Flash 结果未混入本轮。

- `report.json`：原始逐题结果、消息、证据快照、工具轨迹、usage和全部attempt。
- `report.md`：48个计划组合的状态及机器汇总。
- `review-packet.md`：实际答案、预期事实、指标和助手复核说明，便于人工逐条审阅。
- `assistant-review.json`：绑定report/dataset/case/variant/run身份的审核草稿，`review_source=assistant_draft`。

已执行16道开发题×两模式。最后4个组合出现PermissionDeniedError；一次独立最小请求
确认HTTP 403、`AllocationQuota.FreeTierOnly`，见 [接口复查](../pro-connectivity-recheck.json)。
尚未冻结和运行8道mall-tiny保留题×两模式，报告保留全部16个not_run，不补造成绩。
恢复平台权限后，应先确认配置摘要一致，再冻结并执行保留集。
每批最多4个任务；每个组合仅一次attempt，不删失败、不挑最好结果。
本轮没有修改源码、提示、检索规则、模型配置或预算。默认输出上限2048 token，
8次模型请求、16次工具、180秒任务时限、90秒模型时限、60000输入字符。
所有人工审核仍待确认，`success_rate=null`，`analysis_ready_for_programming=false`。
免费额度相关限制的具体原因（额度耗尽、免费模式开关、模型授权等）需控制台核实，
不能仅凭错误码断言欠费。本次没有替用户修改计费配置或重试这些失败组合。

## 已观察到的具体问题

1. `petclinic-visit` 两模式均 `invalid_answer`：修正请求usage显示2048个completion token全部是reasoning token，未得到合法最终结构。
   这是输出预算可能不足的证据；当前适配器没有保存finish_reason，不能把原因写成已被完整证明。
2. `flask-session-open/literal` 因 `max_rounds` 停止：多次read_file请求超过120行，返回invalid_range。
   indexed模式读取多个较大片段后context_budget终止，不能靠找到相关文件就计成功。
3. `petclinic-runtime-overload/literal` 文字明确无法确认线上对象，却给出sufficient/completed。
   根据当前无答案题规则必须insufficient_evidence，因此即使文字被人工认可也不满足成功条件。
4. `flask-test-session/indexed` 找到了open/yield/save和默认后端，但把resp创建描述在null判断之后。
   实际源码先构造resp再检查null。草稿标记局部顺序错误，严重性由人工逐项确认。
5. `petclinic-owner-search` 两模式解释了分页，但未明确写出标注中的JpaRepository继承关系。
   引用覆盖不代表解释完整；该项是否关键遗漏需要人工判断，不能由助手改标签来提高分数。

这些观察支持下一轮优先研究工具参数约束的提示、按符号范围精读、剩余预算下的取证停止策略、
输出预算配置及不足回答状态的一致性。它们是后续改进方向，本轮未调整后重跑。
任何基于本次mall-tiny结果的调优都会使其成为开发数据；再次声称未见保留集效果时须选择新仓库。

## 人工审核

逐题对照固定源码、实际证据、预期事实和不确定项。草稿不是成绩，不应批量把来源字段改成human。
完成实际审核后填写真实reviewer、修正事实判定/遗漏/失败分类，再按
[导入说明](../../paired-evaluation.md) 生成新报告，保留本目录原始记录。
旧MVP十题另有审核要求，不能用本报告代替。

源码摘录来自公开固定基准，许可证及上游地址见
[上游声明](../../../benchmarks/upstream-notices.md)。没有运行这些项目的业务服务或构建。
