# Spec Delta

## Purpose

以版本固定的独立真实仓库衡量分析 Agent 的定位、解释和拒答能力，使工程回归、真实模型回答和人工语义审核具有不同且可追溯的证据。通过可重放的原始模式对照和保留仓库验证，支持实习项目的能力说明及后续编程阶段决策。

## ADDED Requirements

### Requirement: Independent versioned benchmark corpus
基准 SHALL 包含至少3个独立上游真实仓库，其中至少2个Java/Spring Boot仓库及1个Python仓库，每仓库至少20个可读源文件、8题，总计至少24题。五类问题（入口、跨文件、配置、异常、无答案）各至少3题，并包含同名符号或多实现歧义。每仓库记录来源、固定完整提交号、许可证来源、允许文件清单及内容摘要；测试用人工小夹具不得计入真实仓库数量。

#### Scenario: Repository revision mismatch
- **WHEN** 本地准备的仓库提交号、允许文件清单或内容哈希不符合标注版本
- **THEN** 拒绝生成该基准的可比成绩，报告不一致位置；不以当前HEAD或忽略变更的方式静默替代

#### Scenario: Missing or inaccessible benchmark checkout
- **WHEN** 默认离线CI没有下载外部基准仓库
- **THEN** 小型夹具回归仍可运行，真实基准状态为not_run；显式请求真实基准时列出缺失项，不自动克隆或启动目标业务服务

### Requirement: Separate annotations from inference
真实运行 SHALL 只向模型提供问题及允许的工具结果，不提供 expected_files、expected_facts、标注片段、参考检索词、人工评分或预设工具轨迹。新基准协议v2与原v1数据集兼容读取，明确区分模型结果协议版本、评测数据版本及报告版本。

#### Scenario: Annotation leakage sentinel
- **WHEN** 标注中植入不在问题及源码中的唯一标识
- **THEN** 真实执行的模型消息和工具参数中不出现该标识；离线固定脚本如使用答案位置必须显式标为控制链路模拟，不参与能力比较

### Requirement: Held-out repository discipline
基准 SHALL 在调整检索规则前固定开发集与保留集，其中至少一个Java仓库的全部问题进入保留集。记录数据集摘要、规则版本及冻结点；冻结前不得用保留题的运行结果调优，查看后据此修改则必须披露并重新指定独立保留集后再声称未见仓库效果。

#### Scenario: Tuning based on held-out failure
- **WHEN** 开发者读取保留集结果后修改排序权重或提示策略
- **THEN** 报告将该仓库标记为已用于开发，不能继续把同一组题的结果标成未见评测

### Requirement: Paired bounded real execution
评测 SHALL 支持literal与indexed成对运行，使用相同问题、仓库版本、模型配置和任务预算。真实调用必须显式启用；默认每次最多运行4个case-mode组合，支持指定题目、上限和从兼容记录续跑。失败和未运行组合保留在计划分母中，不静默丢弃；没有凭证或服务不可用时不得伪造成绩。

#### Scenario: Resume after partial evaluation
- **WHEN** 一次限额只执行了24题乘2模式中的4个组合
- **THEN** 报告标记4个已执行及44个未运行，续跑仅接受相同仓库/数据集/模型/预算/规则版本，保留旧run_id和失败记录，不重复计分

#### Scenario: One mode fails
- **WHEN** 同一题literal成功而indexed超时或反之
- **THEN** 两个状态均保留在成对报告中，失败不被当作缺失数据剔除，报告同时展示完整计划数与实际运行数

### Requirement: Multidimensional comparison with manual review
报告 SHALL 分别记录文件覆盖、引用有效性、人工事实正确/遗漏/合理拒答、失败分类、模型/工具调用、实际耗时和usage，并给出literal/indexed逐题差异及明确分母。检索候选Recall@5等定位指标必须区分离线检索测试与真实Agent整体能力；无引用、无usage、未审核和未运行保持未知或明确未完成，不能推测价格或宣称统计显著。

#### Scenario: Relevant file with unsupported explanation
- **WHEN** 找到了预期文件且引用合法，但人工审核结论错误
- **THEN** 定位指标与语义失败同时显示，该题不计为语义成功，不能以引用有效率替代答案正确率

#### Scenario: No improvement over baseline
- **WHEN** 增强模式没有提高定位或语义表现，或额外耗时更高
- **THEN** 如实输出负面/持平结果及失败类别，不删题、不更换模型后混算，也不宣称未经证实的优化收益

### Requirement: Analysis readiness and programming roadmap boundary
分析阶段 SHALL 交付已审核的成对真实报告和失败复盘，并分别记录“功能实施完成”与“达到编程阶段建议门槛”。门槛为24题两模式全部审核、indexed整体及保留集语义成功率均至少75%、无已知未修复的只读边界或引用校验回归，且相对literal语义成功数不降低；这些是拟验收目标而非当前结果。编程路线图只描述后续阶段，不自动启用写入或执行工具。

#### Scenario: Quality gate not reached
- **WHEN** 分析功能和测试已完成，但真实报告缺失或质量门槛未达到
- **THEN** 明确记录未达到的条件，继续分析改进，不将未来编程能力标为已实施，也不自动放宽验收门槛

#### Scenario: Gate satisfied
- **WHEN** 记录满足分析阶段门槛
- **THEN** 仅形成后续编程提案的依据；隔离工作区、补丁、限定测试、权限和回退仍需独立提案，不属于本变更实施任务
