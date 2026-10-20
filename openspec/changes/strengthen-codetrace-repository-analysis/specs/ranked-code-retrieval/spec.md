# Spec Delta

## Purpose

为代码定位增加可解释的相关性排序，减少无序关键词命中占用有限上下文的问题。增强检索与原有字面量工具并存，具有明确的模式、预算和记录，使改造效果能够在相同仓库、问题与模型条件下接受对照检验。

## ADDED Requirements

### Requirement: Deterministic ranked search
系统 SHALL 提供只读排序检索，输入为1至200字符查询、可选子路径/后缀、top_k（默认5，范围1至20）。结果综合标识符、路径与文本匹配，包含文件、行范围、有限摘要、分数构成、索引版本及截断原因；相同静态索引与查询返回稳定顺序，无匹配返回空结果。

#### Scenario: Identifier variants and ties
- **WHEN** 源码包含 camelCase、snake_case 标识符以及同分候选
- **THEN** 分词规则支持完整标识符和组成部分匹配，同分结果按路径和行号稳定排序，重复候选不占多个排名

#### Scenario: Chinese query without matching identifiers
- **WHEN** 中文问题的词语未出现在标识符、路径或源码文本中
- **THEN** 允许返回无匹配，不假装具备语义翻译能力；模型可以根据工具结果自行改写查询，仍受任务预算约束

#### Scenario: Context bounded by result limits
- **WHEN** top_k和摘要字符预算达到上限
- **THEN** 返回已选择候选并说明截断，不把超量全文塞入模型上下文；最终事实引用仍需要单独读取源码

### Requirement: Explicit retrieval mode compatibility
CLI及评测 SHALL 支持 literal/indexed 检索模式，默认literal保留既有工具名、参数、范围和离线场景行为；indexed显式增加符号导航和排序搜索。实际允许的工具集合、提示说明、模式和版本须一致记录，非启用工具请求返回unknown_tool，未知模式为参数错误。

#### Scenario: Existing offline command
- **WHEN** 用户不指定新模式，运行原有四种离线场景
- **THEN** 保持原场景、退出码和schema_version=1结果契约，不初始化索引或新增模型请求

#### Scenario: Model requests disabled indexed tool
- **WHEN** literal 模式收到排序搜索或符号查询请求
- **THEN** 工具执行层拒绝请求，不仅依靠提示词隐藏工具；indexed 模式则可以调用这些工具

### Requirement: Unified execution limits
新增检索与导航工具 SHALL 使用已有模型、工具、时间和上下文预算，首次索引开销也受总时限限制；修正阶段继续禁用所有工具。重复调用判定必须基于实际候选数据与版本，不能因耗时、随机ID或使用次数变化就将相同结果认作新增信息。

#### Scenario: Repeated search without progress
- **WHEN** 模型连续请求相同排序搜索，源码及候选没有改变
- **THEN** 第二次提醒、第三次实际搜索不执行并按已有 repeated_calls 规则停止，元数据变化不重置重复计数

#### Scenario: Exhausted budget before indexed tool
- **WHEN** 工具批次超过剩余预算或索引过程中任务超时
- **THEN** 保留原协议配对和停止语义，不在预算外继续检索或请求最终总结

### Requirement: Comparable retrieval traces
任务记录 SHALL 在保持现有结果结构可解析的前提下记录模式、检索实现版本、有效索引参数、候选排序、建索引耗时与检索耗时。记录不包含配置密钥，失败只保存经处理的错误类别；索引与原有重复检测开销须纳入实际任务耗时。

#### Scenario: Compare two modes
- **WHEN** 相同问题在literal和indexed模式各执行一次
- **THEN** 两条记录可辨认工具集合及参数差异，并保留各自run_id、原始usage和耗时，不把额外索引工作从总耗时扣除
