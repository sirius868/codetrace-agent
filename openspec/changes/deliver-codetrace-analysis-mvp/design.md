# Design

## Context

动机见 proposal.md。当前 `graph.py` 为 model/tools 双节点图，最终答案在 model 节点内用正则检查引用；非空无引用答案仍能 completed。`repository.py` 支持目录搜索但不能搜索单文件，目录扫描顺序未稳定，`read_file(start>80)` 省略 end 会触发默认范围问题。`models.py` 已有 OpenAI SDK 适配及固定 main 定位 DemoModel；`cli.py` 可保存原始状态但无版本化契约。现有 tests 覆盖基础边界、预算、并发隔离和模拟 HTTP，不覆盖完整 CLI 或业务评测。

Python 3.12 / Windows 是主开发环境；用户无 API Key，开发与 CI 必须离线可验。项目不是空仓库，不重建现有环境，也不引入 backup 代码。跨模块数据契约和路由均有变化，因此需要本设计文档。

## Goals / Non-Goals

**Goals:**
- 把“执行成功”“证据不足”“引用可核对”“答案正确”拆成不同指标，支持可解释的实习面试演示。
- 将工具、图编排、模型协议、结果记录和评测保持为小模块，单个学生能追踪完整调用链。
- 在有限轮数和有限上下文下完成入口、跨文件和配置问题；用确定性测试保证失败路径。

**Non-Goals:**
- 不把文本搜索包装成全程序静态分析，不承诺动态调用链完整或语义正确自动可证。
- 不实现不可信并发文件系统的 OS 沙盒，不提供文件读取硬取消保证。
- 不增加持久化恢复或并行分析分支；串行节点不引入复杂 reducer。

## Decisions

### 1. 保留当前包结构，显式分离回答校验

图调整为 START → model；工具请求 → tools → model；最终响应 → validate；失败且修正预算可用 → repair → validate；其他情况 → END。保留 LangGraph StateGraph，拒绝在节点内嵌套独立 Agent while 循环。

`contracts.py` 定义结果/证据契约，`evidence.py` 管理结构和引用检查，`evaluation.py` 管理评测；原 graph/models/repository/cli 继续承担原职责。Pydantic 显式列为直接依赖用于严格数据校验，因为项目已间接依赖它，较手写深层 dict 检查更易测试。更新依赖快照，不升级 LangGraph 主版本。

替代方案：仅扩展系统提示词无法约束“无引用也成功”；通用多 Agent 框架会增加无必要的上下文和调试成本。

### 2. 模型最终文本承载结构化 JSON，程序渲染答案

最终响应契约为 `{findings:[{text,citations:[{evidence_id,path,start,end}]}], uncertainties:[str], evidence_status:'sufficient'|'insufficient'}`。不接受自由文本外加猜测性解析；兼容去除完整包裹的一层 JSON code fence，但不从任意文字中提取片段。限制 findings≤20、每条引用≤8、字符串长度，并禁未知字段。程序从核验过的结构渲染 Markdown，原 answer 字段保留为派生展示文本。

每次 read_file 成功分配任务内 evidence_id，保存相对路径、范围、原文片段和整文件 SHA-256；重复快照可去重，不跨任务复用。代码事实无引用不通过校验。insufficient 允许空 findings，但必须有具体 uncertainties；语义诚实仍需人工评测。

选择最终文本 JSON 而非供应商特有 structured output：先支持通用 tools 接口，避免不同国内模型的 JSON schema 能力差异成为硬依赖。解析失败也进入一次 repair；repair 发出工具禁用请求，只提供原问题、候选结果、校验错误及已有证据。SDK 不支持工具禁用响应或返回新工具调用时按无效修正处理。

### 3. 有界稳定遍历和更实用的工具

提取统一路径校验和遍历，所有入口复用。每目录只收集剩余目录项预算允许的条目后排序；达到预算时明确截断，稳定顺序保证针对未耗尽扫描预算的静态目录。按后缀统计，仅把 README、pom.xml、build.gradle、pyproject.toml 等作为候选，不据此推断实际启动路径。

list_files 默认100、最多500文件；搜索候选最多500，结果最多100，匹配上下文0至3行。读取保留256000字节、120行及12000字符上限；默认 end 改为 None 后按 start+79 计算，next_start 在文件未读完时给出。空文件明确返回空 lines、无可引用范围。

新增 repository_overview 工具；列表、搜索支持目录范围和后缀过滤，搜索额外支持单文件。暂不增加索引或 rg 子进程，以便跨平台部署和直接测试参数边界。后续确有性能数据再替换搜索后端。

### 4. 预算按真实调度计数，保留协议完整性

状态增加 model_attempts、repair_count、deadline、context_chars、规范化调用历史及任务结果。保留 rounds 为成功模型响应轮数；model_attempts 在发起请求前计数，所有修正也占最大轮数预算，失败调用不被“免费重试”。SDK 内部最多一次网络重试受同一节点超时和总 deadline 约束。

默认8次模型尝试、16次工具实际执行、180秒任务总时限、90秒节点时限、60000字符输入。提示词、完整消息和工具定义均计入请求输入字符数。输入超限直接 context_budget，不随意删除尚未配对的工具消息，也不声称字符数等于 token。停止时保留已有证据，不强制再花一次模型调用生成“总结”。

工具名和排序键 JSON 参数构成调用签名；结果摘要/哈希构成进展标识。连续相同且无新证据时累计，第二次提供提醒，第三次请求不执行并停止。只有成功读取的新片段、快照变化、或新搜索结果才算进展；按签名与结果建立单元测试避免合法重复被误停。原调用批次中的每个已收到 call ID 都需工具响应；提前停止的剩余项写 skipped 结果，不继续请求模型。

### 5. CLI 与任务记录

CLI 参数保持兼容，增加 `--scenario`（离线场景）、`--timeout`、`--max-context-chars`。默认 offline 场景仍为 entry，新增 cross-file/config/no-answer；模拟模型按当前消息决定下一步，不用共享可变计数器。缺省问题随显式场景显示，不声称离线理解任意问题。

结果信封包含 schema_version=1、run_id、mode、question、repo_root、配置的模型名、预算、结果状态、findings、uncertainties、evidence、trace 和 usage。trace 中模型/工具分开记录，工具包含参数、call_id、耗时、截断/错误；原始异常字符串不落盘。默认不保存源码，`--trace-dir` 显式启用完整记录；新文件写临时文件后原子替换，失败退出2，文档说明记录含源码。

completed 与 insufficient_evidence 正常退出0，其他运行停止1，配置/参数/输出错误2。旧状态导出不承诺恢复，新增 JSON schema 版本并在文档解释兼容变化。

### 6. 评测与开发闭环

在 examples 中维护小型 Python/Java 仓库，数据集存 JSON：id、repo、manifest_sha256、category、question、expected_files、expected_facts、answerable、acceptable_uncertainties。至少10题，每语言至少4题，每类别至少2题，避免仅靠样例名称打分。仓库清单按受测文件相对路径排序后对内容哈希求汇总，包含所有夹具源码和配置；排除不属于夹具的运行产物。

新增 `codetrace-eval` 入口，默认 offline；`--live` 才访问模型。自动计算预期文件覆盖、合法引用/全部引用、结束状态、调用量、耗时与实际 usage。无引用分母为0时结果为 null；语义正确、事实遗漏和合理拒答由人工按标注填写。汇总按模式分离，未知值不填0，报告写明样本量和已审题数。

测试层次：Repository 临时目录测试；图用注入式模拟模型；适配器用 HTTP mock；CLI 用子进程验证退出码与记录；评测用固定输入验证指标。真实模型 smoke test 提供可执行命令，缺少凭证时记 not_run，不阻塞离线实现交付，但完整真实能力验收不能标完成。

## Risks / Trade-offs

- [模型不能稳定输出 JSON] → 小契约、输出示例、一次修正；失败明确呈现，不用多轮修正掩盖问题。
- [有效引用仍可能支持错误结论] → 人工标注与语义评分；不宣称自动校验解决幻觉。
- [字符预算使大仓库任务较早停止] → 工具可缩小范围、逐段读取；第一版拒绝粗暴历史截断。
- [链接和并发文件变更] → 路径校验、reparse 拒绝、证据快照；说明正常本地仓库假设。Windows 权限不足时跳过真实 symlink 创建，但用属性注入覆盖拒绝分支。
- [关键词重复检测误判] → 仅停止连续相同、无新增信息的请求，变化结果和不同参数允许继续。
- [真实 API 缺少凭证] → 开发默认离线，完成协议 mock；在线验收单独保持未完成状态。
- [任务扩大导致本科生难以掌握] → 保持单进程 CLI、文本检索与串行图，按里程碑交付，不增加服务拆分。

## Migration Plan

1. 保留现有入口/测试作为回归基线；先新增契约、工具及测试，再切换图的最终结果路径。
2. 更新 DemoModel 为合法结构化输出，同步 SDK mock、CLI 退出码及旧测试断言；把行为变化写入 README。
3. 增加评测夹具、报告和文档，重跑完整离线测试、pip check、CLI 演示和评测数据校验。
4. 按实现任务分批提交，每次附测试；如需回退，使用相应 commit 的 revert，保留用户配置与 runs 数据。当前不涉及数据库迁移。
5. 有凭证后人工选择模型执行真实 smoke/评测，记录模型及日期，不把离线阶段的报告改成真实结果。

## Open Questions

- 用户之后选择 DeepSeek 还是通义千问，仅影响本地配置和真实兼容性记录，不改变接口及任务划分。
- 真实模型输出稳定性和耗时只能在接入后测量；首次10题不预设提升比例或成功率承诺。
