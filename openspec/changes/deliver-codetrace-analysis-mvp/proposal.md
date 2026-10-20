# Proposal

## Why

CodeTrace 已有可运行的 LangGraph CLI、三个只读工具和模拟模型测试，但离线演示只定位一个 Python main 函数，尚不能形成可验证的跨文件分析、证据不足处理和求职展示闭环。现在需要在现有实现上完成一个本科生可以理解、独立演示、用测试与评测解释工程取舍的仓库分析 MVP。

## What Changes

- 保留 CodeTrace 名称、Python 3.12、本地单仓库 CLI 和 LangGraph StateGraph，增加仓库概览、可缩小范围的搜索及读取续页。
- 建立显式的回答校验节点，支持入口定位、跨文件流程、配置追踪和证据不足回答；每条代码事实关联本次读取证据，校验失败最多修正一次。
- 保留国内 OpenAI 兼容模型适配，扩展无凭证离线场景及模拟 HTTP 集成测试；真实 API 验证列为有凭证后独立验收，绝不把模拟通过表述为真实模型通过。
- 增加任务级预算、重复无效调用控制、上下文大小上限和版本化执行记录；不依赖数据库或付费观测平台。
- 提供两个小型 Python/Java 样例仓库、至少 10 条人工标注问题、离线与真实模型分开的评测报告、运行文档和面试讲解材料。
- **BREAKING**：原有任意非空无引用文本可返回 completed；新行为要求代码事实通过结构及证据范围检查，证据不足用独立状态表达。状态/结果 JSON 升级为 schema_version=1，保留现有 CLI 参数并提供迁移说明。
- 不纳入 Web 前端、FastAPI、Java 服务集成、向量库、多 Agent、检查点恢复、远程仓库克隆或任意代码执行；保持中等复杂度与低成本。

## Capabilities

### New Capabilities

当前 OpenSpec 无已归档能力规格；以下规格在明确现有约束的基础上定义新增及强化后的业务契约。

- `repository-exploration`: 有界只读访问、仓库概览、指定文件/目录搜索和可继续的片段读取。
- `evidence-analysis`: LangGraph 多步分析、结构化事实与证据、引用核验、一次修正及证据不足终止。
- `analysis-execution`: 模型配置、离线模式、执行预算、任务隔离、CLI 和版本化记录。
- `analysis-evaluation`: 固定样例与标注、离线回归、真实模型评测、指标和可复现交付。

### Modified Capabilities

无既有 OpenSpec 规格。

## Impact

- 主要修改 `src/codetrace/repository.py`、`graph.py`、`models.py`、`cli.py`，按职责提取结果契约、证据校验及评测模块，扩展 `tests/` 和 `examples/`。
- 更新 README、架构及交接文档、依赖快照；必要时增加 CI。当前应用代码独立于 `../backup`，不引入旧项目依赖。
- 保留现有工具名、`--repo`、`--question`、`--offline` 和预算参数；扩展参数必须有默认值。真实调用可能产生供应商费用，默认开发/CI 不联网调用模型。
- 改动按任务分批测试并提交 Git；不伪造模型效果、费用或面试经历。用户目前无 API Key，真实能力验收保持待验证状态。
