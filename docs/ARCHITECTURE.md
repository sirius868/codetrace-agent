# 执行状态与工具契约

主流程由 LangGraph StateGraph 的 model、tools、validate、repair 四个节点组成：

```mermaid
flowchart LR
  START --> model
  model -->|工具请求| tools
  tools -->|结果| model
  model -->|最终JSON| validate
  validate -->|一次修正| repair
  repair --> validate
  validate -->|有效或再次失败| END
  model -->|失败或超预算| END
  tools -->|超时或重复| END
```

schema_version=1 的结果契约与样例见 [RESULTS.md](RESULTS.md) 和 [answer-examples.json](answer-examples.json)。旧版任意非空文本 completed 已移除。validate 检查结构及本次 evidence_id、路径、行号；repair 最多一次且禁用工具，也计入请求预算。insufficient_evidence 与 completed 分开统计。引用检查不证明语义正确。

状态包含完整消息、rounds（有效模型响应数）、model_attempts（请求尝试数）、tool_count、repair_count、证据、调用历史和 trace。无持久化检查点；每次 analyse 创建独立图和 run_id。read_file 返回内容快照及SHA-256，登记后向模型返回任务内 evidence_id。相同片段去重，文件变化产生新证据。

默认最多8次模型请求、16次工具调用、单次模型90秒、任务总计180秒、输入60000字符。修正受相同预算限制。上下文计入消息与工具定义，不静默删除工具协议消息。字符数不是计费token。工具批次超预算整批跳过，每个call_id仍有工具响应。总时限后不再调度新操作，不保证硬取消操作系统中阻塞的文件线程。

相同工具与规范化参数连续重复时，比对有界仓库内容指纹及结果；第二次无新增信息时提醒，第三次相同且仓库未变化时停止。内容或参数变化允许继续。指纹检查本身也消耗时间，仅适用于当前小型本地仓库；不是增量索引。异常只记录类型，不保存供应商异常正文。

工具契约见 [TOOLS.md](TOOLS.md)。系统无Shell、Python执行、文件写入工具，仓库文本不能改变工具授权。仓库路径保护不是针对恶意并发修改的OS沙盒。用户可显式保存trace或Markdown报告，路径必须在目标仓库外。

## 索引扩展

每次analyse创建ToolRegistry，literal保留四工具，indexed增加三工具；定义序列化快照与执行白名单一致。
模型与repair接收独立副本，不能修改后续工具定义。即使并发任务共用Repository实例，索引状态仍隔离。
索引经共享_path/_raw/_walk安全层读取，懒构建后保存文本/哈希/语法树。
Tree-sitter Java和Python ast产生词法定义；关系只解析有限显式继承，不能证明动态绑定。
BM25排名候选与symbols都不登记证据；只有read_file经register生成引用ID。

重复比较去掉diagnostics中实例ID、计时和累计计数，保留候选内容与sha256。
返回前复核候选文件；index_stale使下一查询刷新，已登记证据不被改写。
初次清单不自动发现新增文件。索引和指纹均消耗现有任务时限，协作取消不是OS硬取消。

报告由Result纯函数渲染，原子写入。v2评测位于执行图之外，通过只接收question/root/variant的
infer适配运行，标注只用于运行后的指标计算。数据版本2不改变Result版本1。
评测可按组合恢复，LangGraph单任务本身没有checkpoint恢复。
