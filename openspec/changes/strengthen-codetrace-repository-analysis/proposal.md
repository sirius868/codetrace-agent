# Proposal

## Why

CodeTrace 已有只读 LangGraph 分析闭环和一次真实模型跨文件验证，但现有评测仓库各仅3个文件、20行，字面量搜索缺少符号定位和相关性排序，尚不足以证明陌生业务仓库分析能力。本变更将它完善为独立的仓库理解 Agent，以 Java/Spring Boot 为首要验证场景并保留 Python 支持，为以后受限代码修改提供可验证的分析基础。

## What Changes

- 建立任务内有界源码索引，复用现有路径保护，记录扫描范围、文件哈希、索引耗时及截断/解析失败；Java 使用语法解析，Python 使用标准库 AST，不启动目标项目。
- 增加符号定义与静态关系候选定位，覆盖类、接口、方法/函数、显式继承/实现、注解和导入线索；保留歧义，不宣称完整调用图或运行时依赖注入解析。
- 增加确定性排序检索，将标识符、路径和文本匹配结合；保留原 search_code 字面量语义，通过显式 indexed 模式启用新工具，引用仍必须来自 read_file。
- 提供基于已验证结果的 Markdown 分析报告，展示问题、事实/引用、无法确认事项、检索范围和执行统计。
- **BREAKING**：为保持目标仓库只读，新增报告及原有trace输出均拒绝写入被分析根目录内部；分析本项目时应把输出目录设在本项目外部，普通 examples 场景不受影响。
- 扩展版本化评测：至少3个独立真实仓库、至少24题，其中至少2个 Java/Spring Boot 仓库及1个 Python 仓库；包含保留仓库集、运行失败、无答案和歧义，比较原始字面量模式与增强模式，隔离标注与模型输入。
- 完成原 MVP 的剩余真实验收，并把跨仓库结果、人工审核和失败案例作为分析阶段交付依据；开发/CI 仍可离线运行。
- 编程阶段只记录路线图和进入条件：分析报告 → 修改建议 → 隔离工作区中的有限补丁与限定测试。该阶段的写文件、命令执行、回滚和权限设计不在本次实施范围。
- 不增加 Web/FastAPI、账户系统、向量数据库、多 Agent、目标仓库自动克隆或持久化会话恢复；保留现有 CLI 和 schema_version=1 结果，新增评测使用独立v2协议并兼容旧v1数据集。

## Capabilities

### New Capabilities

- `repository-index`: 有界的任务级源码清单、版本关联、索引状态及跨任务隔离。
- `code-navigation`: Java/Python 符号及有限静态关系候选定位、源码核验与分析报告。
- `ranked-code-retrieval`: 标识符和文本的确定性排序检索、可切换工具集合及检索执行记录。
- `cross-repository-evaluation`: 独立仓库基准、无标注泄漏的对照评测、人工审核及进入编程阶段的证据门槛。

### Modified Capabilities

无已归档主规格可修改（openspec list --specs 为空）。本次新增规格扩展在途 `deliver-codetrace-analysis-mvp` 的 repository-exploration/evidence-analysis/analysis-execution/analysis-evaluation 行为，不复制或更名其已有要求；旧变更剩余6.3/6.4继续单独跟踪，不自动归档。

## Impact

- 扩展 repository.py、graph.py、cli.py、evaluation.py；新增独立索引/解析/排序/报告模块及对应测试，保持 models.py 的兼容接口和证据验证职责。
- 计划新增 Tree-sitter 与 Java grammar 依赖，在 Windows/Linux Python 3.12 核验后锁定版本；不新增 embedding API 成本。
- 新增基准清单、标注和实测报告。外部仓库由开发者准备，清单记录真实来源、许可证和固定提交，不将外部仓库或凭证批量提交到本项目。
- 以当前源码及已提交的单例 DashScope 实测为基线；规划文档中旧的“尚无API Key”为历史背景。已只读核实三个基准候选的身份及提交（见design）；源码标注、完整许可证文本和本地准备仍需实施阶段核验，不能伪造测试结果。
- 本次仅生成规划文件；应用代码、README现有用户改动、密钥和原有未跟踪配置保持原状。实施阶段按小批次测试并提交，真实报告与离线模拟严格区分。
