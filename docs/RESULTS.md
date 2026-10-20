# 结果协议 schema_version=1

最终回答使用 `contracts.Answer`，示例见 [answer-examples.json](answer-examples.json)。`valid` 是合法代码事实结构，`insufficient` 是合法证据不足结构，`invalid` 因缺少引用而失败。合法结构仍需与任务内 Evidence 核对，不能证明语义正确。

每条 finding 必须有非空 text 及1至8条 citation；最多20条 finding。citation 包含 evidence_id、相对路径、起止行号，禁止逆序范围、布尔行号和未知字段。insufficient 必须提供 uncertainties。Evidence 保存连续实际行、路径、范围和 SHA-256，不允许空片段。

Result 信封采用 schema_version=1，包含任务ID、模式、配置预算、状态、消息、证据和执行记录。validate 节点已移除旧版本“任意非空无引用文本也能 completed”的规则。模型修正使用 tool_choice=none，供应商仍返回工具调用时拒绝。
