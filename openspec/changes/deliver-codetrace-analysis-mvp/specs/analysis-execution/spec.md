# Spec Delta

## Purpose

使 CodeTrace 的单仓库分析任务能够在普通开发电脑上独立运行、限制模型和工具消耗，并留下可诊断的任务记录。离线练习和真实模型调用分别标识，便于低成本学习和诚实展示验证结果。

## ADDED Requirements

### Requirement: Explicit model modes
系统 SHALL 支持不需要凭证、不初始化网络模型客户端的 offline 模式，以及通过 CODETRACE_API_KEY、CODETRACE_BASE_URL、CODETRACE_MODEL 配置的兼容模型模式。保留原 CLI 参数，不自动读取目标仓库中的配置；启动配置错误在请求前报告。

#### Scenario: Offline without credentials
- **WHEN** 未设置任何模型变量且使用 `--offline`
- **THEN** 执行固定模拟场景并标注模拟模式，不访问真实模型或收费服务

#### Scenario: Missing live configuration
- **WHEN** 真实模式缺少模型地址、名称或密钥
- **THEN** 在发送请求前以配置错误结束，退出码为2，不输出密钥

### Requirement: Bounded task execution
系统 SHALL 校验正整数轮数和工具预算，默认8轮和16次工具调用；任务默认总时限180秒，单轮模型时限90秒，超限后不再调度新操作。最终结果区分模型失败、任务超时、轮数耗尽、工具数耗尽和上下文预算耗尽。

#### Scenario: Batch exceeds remaining tools
- **WHEN** 一轮返回的工具数量超过剩余工具预算
- **THEN** 整批不执行，保留之前证据并以 `max_tools` 结束

#### Scenario: Task deadline
- **WHEN** 总时限到达
- **THEN** 返回 `task_timeout`，不再调用模型或新工具；不宣称可强制取消已阻塞的操作系统文件读取

### Requirement: Repeated ineffective call limit
系统 SHALL 记录规范化工具名及参数，对连续三次相同且无新增证据的调用结束为 `repeated_calls`；第二次重复后反馈提醒。文件版本变化或参数变化不能被错误视为同一无效调用。

#### Scenario: Repeated empty search
- **WHEN** 模型连续三次提交完全相同的无命中搜索
- **THEN** 第三次不再实际执行搜索，结果报告重复停止原因和此前结果

### Requirement: Context size bound
系统 SHALL 在每次模型请求前检查序列化输入的字符数，默认不超过60000字符；超限返回 `context_budget`。本版本不通过任意截断工具消息来规避预算，不将字符上限宣称为精确 token 计费限制。

#### Scenario: Large accumulated evidence
- **WHEN** 加入工具结果后下一次请求超过字符上限
- **THEN** 不发送该请求，保留已有记录并说明上下文预算耗尽

### Requirement: Versioned isolated run records
系统 SHALL 为每次任务分配 run_id；选择保存记录时输出 schema_version=1、运行模式、问题、仓库标识、状态、模型及工具耗时、调用参数、错误类型、证据和原始 usage。任务状态互不共享，不存 API Key 或供应商原始异常字符串，缺失 usage 记为未知而非0。

#### Scenario: Independent tasks
- **WHEN** 同进程运行两个问题
- **THEN** run_id 不同，消息与证据隔离，记录能够对应各自问题

#### Scenario: Safe failure trace
- **WHEN** 供应商抛出含密钥文本的异常
- **THEN** 记录只保留分类与脱敏诊断信息，不包含密钥或原始异常正文

#### Scenario: Save or fail visibly
- **WHEN** 指定 trace 输出且文件系统写入失败
- **THEN** 明确报告记录未保存并以退出码2结束，不打印成功保存路径

### Requirement: CLI result semantics
系统 SHALL 展示 findings、证据、未确认事项和停止原因；completed 与正常的 insufficient_evidence 退出码为0，但结果状态不同。执行失败、校验失败及预算终止退出码为1，输入或记录保存错误为2。旧的非空文本不能绕过新结果核验。

#### Scenario: Human and machine consumers
- **WHEN** 运行得到证据不足结果
- **THEN** 终端说明无法确认且正常退出，JSON 中明确 insufficient_evidence，评测不得将其计为正确回答
