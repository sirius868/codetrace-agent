# Spec Delta

## Purpose

提供可复现的测试与评测证据，让开发者能够区分工具和执行流程是否正确、真实模型回答是否正确，并通过固定仓库和问题集说明 CodeTrace 的能力、失败案例及工程改进。

## ADDED Requirements

### Requirement: Versioned evaluation fixtures
项目 SHALL 提供至少两个小型本地样例仓库（Python 和 Java）及至少10条人工标注问题，覆盖入口定位、跨文件流程、配置追踪、异常处理、无答案五类。每题包含唯一ID、仓库内容哈希、预期文件、关键事实和允许的不足说明；不需要启动样例业务服务。

#### Scenario: Dataset consistency
- **WHEN** 执行评测前校验数据集
- **THEN** 问题ID唯一、预期文件及片段存在，仓库哈希与标注版本匹配；不匹配时拒绝生成可比成绩

### Requirement: Separate offline and live evaluation
系统 SHALL 提供离线回归和显式真实模型评测两种模式，默认不调用付费服务；离线固定响应只验证工具与控制链路。缺少凭证时真实评测标记未运行，不伪造答案或通过率。

#### Scenario: No API key available
- **WHEN** 开发者运行默认评测且没有 API Key
- **THEN** 离线场景可执行，报告标识 offline，真实模型结果显示 not_run

#### Scenario: Live run selected
- **WHEN** 开发者明确选择真实模式且配置有效
- **THEN** 逐题运行同一标注集，记录模型、模式、预算和仓库版本，真实结果与模拟结果独立保存

### Requirement: Honest multidimensional metrics
报告 SHALL 按题输出状态、预期文件命中、引用有效性、模型轮数、工具数、延迟与服务端 usage，另设人工语义判定。缺失 usage 和尚未人工评分保留未知；空引用的有效率不算100%，insufficient_evidence 对有答案问题不算成功。

#### Scenario: Valid citation but wrong conclusion
- **WHEN** 回答引用范围有效但解释不符合人工标注
- **THEN** 引用有效与语义失败分别显示，不把引用检查当成答案成功率

#### Scenario: Unreviewed or missing usage
- **WHEN** 模型未返回 usage 且人工未评分
- **THEN** 对应字段为未知，汇总明确分母和已评数量，不填零成本或推测成功率

### Requirement: Reproducible automated verification
项目 SHALL 提供一条测试命令覆盖工具边界、图路由、预算、修正、模型协议、CLI 和评测计算，并提供离线演示命令及精确依赖快照。默认测试不得依赖真实模型或用户凭证；平台不支持的链接集成测试可跳过，但必须报告原因且有可运行的链接属性拒绝逻辑测试。

#### Scenario: Clean checkout verification
- **WHEN** 在 Python 3.12 环境按文档安装依赖并执行测试及离线演示
- **THEN** 无 API Key 也能完成验证，失败和跳过均可见，不需要浏览器、GPU 或旧项目目录

### Requirement: Reviewable engineering delivery
文档 SHALL 说明实际架构、运行方式、已验证范围、已知限制和至少8个项目相关面试问题的回答线索；功能改动附相关测试及 Git 提交。性能、成功率和个人贡献仅使用真实实现及可追溯报告。

#### Scenario: Interview walkthrough
- **WHEN** 开发者按文档讲解一次跨文件任务
- **THEN** 能定位状态定义、条件路由、工具边界、证据验证和停止原因的源码与测试，未验证的真实模型效果明确标注
