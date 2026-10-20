# 面试讲解与源码导航

以下描述已实现的工程行为。真实模型效果尚未验收；简历不能把离线模拟当成真实任务成功率。建议先从一次 cross-file 的 JSON 记录讲出完整调用链，再逐项回答。

1. **Agent 和调用一次 LLM API 有何区别？** 模型可以根据工具结果决定继续检索或回答，状态在 model/tools/validate/repair 节点间传递。定位 `graph.py:State/build_graph` 和 `tests/test_graph.py`。离线 DemoModel 是固定脚本，不能用于证明自主规划。
2. **为什么使用 LangGraph？** 条件路由将调用工具、最终验证、一次修正和终止显式表达；每个节点可用注入模型独立测试。目前串行单任务状态，无持久化 checkpointer，也不声称支持恢复或多 Agent。
3. **如何限制工具越权？** `repository.py` 统一处理路径、凭证文件、符号链接/reparse、扫描及读取预算；工具只读，不执行仓库代码。阅读 `tests/test_repository.py` 和 `tests/test_exploration.py`。这是正常本地仓库访问边界，不是防恶意并发文件替换的OS沙盒。
4. **为什么搜索命中不直接作为最终证据？** 搜索用于定位，read_file 返回连续原文、整文件哈希和任务内ID。`evidence.py:register/validate_answer` 校验引用路径及范围。正确范围仍可能支持错误解释，因此语义正确性单独人工审核。
5. **模型输出不合法怎么处理？** 严格 Pydantic 契约拒绝额外字段、空事实、非法范围；validate 失败后最多一次 repair，工具被禁用。修正占模型预算，失败返回 invalid_answer。看 `contracts.py` 与图测试的修正成功/失败场景。
6. **如何控制上下文和成本？** 对完整消息、提示词和工具定义做字符预算检查；超限 context_budget 终止，不悄悄删除工具响应。限制模型和工具次数。SDK usage 缺失保持 null；字符数不等于 token 或实际价格，尚未实现价格表计费。
7. **怎么避免无限循环？** 连续相同的规范化工具参数、结果和仓库内容指纹计为重复，第二次提醒，第三次不执行；文件变化允许再读。`graph.py:tools_node` 有轮数和工具数作为兜底。指纹会扫描仓库，适合小仓库，后续优化需要实测。
8. **超时和失败后能保证什么？** model/tools 在剩余总时限内执行，模型失败只记异常类型，批量工具调用即使预算终止也配对 skipped 响应。停止后不再调度；线程中的阻塞文件读取不保证硬取消。原始 trace 可定位失败，当前无自动恢复。
9. **如何证明效果？** `evaluation.py` 校验双语言10题仓库哈希及标注，分开衡量文件覆盖、引用有效性、终止状态、调用量、耗时和人工语义评分。离线只验证链路，真实报告需 --live 和逐题人工审核；看 `tests/test_evaluation.py` 中“有效引用但错误结论”测试。
10. **怎样接国内模型？** `models.py:OpenAICompatibleModel` 通过 base_url/model/key 配置调用兼容 chat completions tools 接口；repair 使用 tool_choice=none。HTTP mock 覆盖401/429、超时及畸形响应，不能替代供应商真实验收。真实结果需记录模型名和日期。
11. **记录如何防止写一半？** `records.py:write_json` 在目标目录创建临时文件，flush/fsync 后 os.replace；异常清理临时文件并让CLI退出2。`tests/test_cli.py` 注入替换失败，验证旧记录不被破坏。记录包含源码，默认不保存。
12. **自己的贡献可以怎么写？** 只写能够定位的实现：四节点状态图、只读工具边界、证据契约与一次修正、预算/重复限制、双语言评测和自动化测试。当前不应写已实现向量RAG、全程序调用图、服务上线或未经测量的成功率提升。Java夹具用于理解Java代码，并不等同于Java后端项目。
