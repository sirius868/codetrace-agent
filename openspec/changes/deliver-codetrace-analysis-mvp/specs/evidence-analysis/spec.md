# Spec Delta

## Purpose

让 CodeTrace 的入口定位、跨文件流程和配置追踪回答具有可核对的源码依据，并把自动可验证的证据范围与仍需人工评估的结论正确性分开，避免把流畅输出当作已证实结论。

## ADDED Requirements

### Requirement: Structured findings and uncertainty
系统 SHALL 输出结构化结果，包含 findings、每条 finding 的 citations、uncertainties 和 evidence_status。代码事实必须关联证据；没有足够证据时返回 `insufficient_evidence`，允许保留已有证据支持的部分 findings，不得宣称完整分析成功。

#### Scenario: Cross-file explanation
- **WHEN** 已读取入口函数及另一个文件中的被调用函数后生成调用链结论
- **THEN** 分别引用两个文件的读取片段，将静态可见调用与无法确认的动态行为区分

#### Scenario: Unsupported fact
- **WHEN** 模型返回没有任何引用的代码事实
- **THEN** 结果不通过结构证据校验，不能返回 `completed`

#### Scenario: Insufficient evidence
- **WHEN** 工具没有提供足以回答的证据或存在无法消除的扫描限制
- **THEN** 输出明确的不足说明与已检查范围；不得将未搜索到直接表述为功能不存在

### Requirement: Snapshot citation validation
系统 SHALL 校验每个引用的 evidence_id、仓库相对路径、起止行号与本次读取快照一致，并检查该区间包含在实际返回片段内。搜索摘要、前一任务证据和仅在磁盘存在的文件不构成有效引用；核验通过不证明结论语义正确。

#### Scenario: Wrong range or missing evidence
- **WHEN** 引用范围超出片段或 evidence_id 属于别的任务
- **THEN** 返回引用校验错误并禁止将该结论标记为已核验

#### Scenario: File changes after reading
- **WHEN** 文件在读取后发生变化
- **THEN** 结果仍关联原读取片段及其 SHA-256，不把原行号宣称为当前磁盘版本的精确位置

### Requirement: Bounded answer repair
系统 SHALL 在结构或引用校验失败时最多执行一次回答修正，并让修正计入模型轮数、时间及上下文预算；修正只使用现有证据、不执行新工具。预算不足或再次失败时保留明确失败原因。

#### Scenario: Successful correction
- **WHEN** 首次答案引用错误且仍有模型预算，第二次响应改为已读取的正确范围
- **THEN** 最终结果通过核验，执行记录包含初次错误和修正次数1

#### Scenario: Repeated invalid answer
- **WHEN** 修正响应仍引用未读文件
- **THEN** 以 `invalid_answer` 结束，不进入无界修正循环，不展示为可信答案

### Requirement: Untrusted source content
系统 SHALL 将仓库文件作为被分析数据，工具能力固定为只读探索；源码中的指令不得改变根目录、工具白名单、预算或配置。

#### Scenario: Instruction embedded in README
- **WHEN** 读到要求执行 Shell 或读取仓库外密钥的内容，随后模型请求此操作
- **THEN** 工具层拒绝该请求，仓库外内容不返回，失败记录保留
