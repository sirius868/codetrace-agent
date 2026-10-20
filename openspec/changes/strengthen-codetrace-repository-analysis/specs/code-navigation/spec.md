# Spec Delta

## Purpose

帮助开发者在 Java 和 Python 仓库中定位定义及有限的静态关系线索，降低仅靠文本搜索处理同名符号和接口实现的困难。所有导航结果保留源码版本与歧义，最终分析仍依赖实际读取证据，并提供可独立审阅的结果文档。

## ADDED Requirements

### Requirement: Symbol definition lookup
系统 SHALL 提供只读符号查询，支持名称、语言、种类及路径范围过滤，返回最多20个候选及截断状态。候选包含名称、限定名、定义类型、路径、起止行、签名及源文件哈希；支持 Java 类/接口/构造器/方法和 Python 类/函数/方法，不宣称支持完整类型解析。

#### Scenario: Overloaded and duplicate definitions
- **WHEN** 不同包或同一类内有多个同名方法
- **THEN** 保留其限定名、签名和源码位置作为不同候选，不擅自合并或选择唯一实现

#### Scenario: Query narrowed to one module
- **WHEN** 查询限定到某个允许的子目录或语言
- **THEN** 只返回该范围候选，非法范围遵守既有路径错误契约

### Requirement: Static relation candidates
系统 SHALL 支持查询符号的显式 extends/implements 关系及其反向候选，返回关系种类、原始类型表达式、声明位置、可解析的候选目标和歧义状态。符号结果同时提供限定长度的导入及注解线索；这些结果只表达源码声明，不证明运行时选用实现或调用一定发生。

#### Scenario: Multiple service implementations
- **WHEN** 两个类显式实现相同 Service 接口
- **THEN** 返回两个实现候选及各自声明位置，不仅凭名称或注解名称推断运行时绑定唯一目标

#### Scenario: Unresolved external or dynamic relation
- **WHEN** 目标来自外部依赖、动态表达式、反射或无法确定的同名类型
- **THEN** 标记 unresolved 或 ambiguous 并保留原文线索，不编造目标源码位置；仍可通过文本搜索继续分析

### Requirement: Navigation results require source evidence
导航结果 SHALL 仅用于定位，不直接获得可用于最终引用的 evidence_id。回答中的跨文件事实必须经过既有 read_file 快照登记和引用校验；只能根据已读源码解释路径，对动态分发、配置覆盖及事务运行行为保留明确不确定性。

#### Scenario: Definition lookup without reading
- **WHEN** 模型只查询符号就尝试把符号ID作为最终证据
- **THEN** 既有校验拒绝该引用，并依照原有一次修正规则处理

#### Scenario: Controller and service explanation
- **WHEN** 已读取 Controller 调用代码和对应 Service 实现
- **THEN** 回答分别引用支持各事实的片段；未读取或无法确定的 Mapper/外部服务环节不得补成已确认的完整链路

### Requirement: Reviewable analysis export
CLI SHALL 支持显式导出 Markdown 分析报告，内容仅来自本次已验证结果及程序记录，包含问题、事实与引用、未确认事项、停止原因、索引覆盖、调用量、耗时和已知usage。报告不额外调用模型，不将语义未经人工审核标成正确；写入失败退出2，不破坏已有目标文件。

#### Scenario: Export verified and incomplete runs
- **WHEN** 用户请求导出一个 completed、insufficient_evidence 或预算终止的任务
- **THEN** 报告准确展示相应状态及实际可用证据，预算终止不包装成完整成功，缺失usage保持未知

#### Scenario: Export target overlaps analysed repository
- **WHEN** 报告或执行记录输出路径经解析后位于目标仓库内部，或经过指向仓库内部的链接
- **THEN** 在运行前拒绝该输出配置且不写入目标仓库；运行产物只能保存在目标根目录之外
