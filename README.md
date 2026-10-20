# 知码 · CodeTrace

基于 LangGraph 的本地只读代码仓库分析 Agent，面向入口定位、跨文件流程、配置追踪和证据问答。独立 Python 项目，不依赖旧 OpenManus 备份。

## 已实现

- model/tools/validate/repair 四节点图，最多一次回答修正。
- 仓库概览、文件列表、指定文件或目录的字面量搜索、按行读取及续页。
- 可选 indexed 模式：任务内安全索引、Java/Python 定义导航、显式继承候选、BM25 词法排名。
- 代码事实必须引用本次读取的 evidence_id、文件及行范围；保存内容快照和SHA-256。
- 模型次数、工具次数、上下文字符、总时限限制，以及连续重复无效调用拦截。
- 四种固定离线场景和 OpenAI 兼容模型接口；显式保存版本化 JSON 执行记录。
- 两个索引离线演示、Markdown 分析报告、三个固定外部仓库的24题成对评测与分批续跑。

引用范围有效不等于语义正确。离线场景只验证工具和控制流程，不理解任意问题。DashScope qwen3.8-27b 的真实验收进度见 [分析阶段验收](docs/analysis-readiness.md)；未完成人工审核前不宣称成功率。没有向量数据库、前端、持久化图检查点或单任务恢复；评测支持从已保存组合继续。

## 安装与测试

在项目根目录使用 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe -m pip check
```

依赖安装需要联网；开发依赖也可用 `pip install -e ".[dev]"` 安装，但精确复现优先使用快照。运行不要求 GPU、Docker、Node.js、浏览器、LangSmith账号或旧项目环境。测试通过不代表真实模型已验收；Windows 无创建符号链接权限时会跳过对应集成测试，属性拒绝逻辑另有可运行测试。

## 离线运行

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --scenario entry
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --scenario cross-file --trace-dir runs
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --scenario config
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --scenario no-answer
```

entry 定位并读取入口；cross-file 实际读取 app.py 和 service.py；config 搜索并读取 TIMEOUT_SECONDS；no-answer 报告预设搜索没有命中且证据不足。前三种结果 completed，最后一种 insufficient_evidence。模拟结果只描述实际读取，不假冒模型推理。

索引与报告演示（完整快照已包含可选解析依赖）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --retrieval indexed --scenario navigation --report runs/navigation.md
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --retrieval indexed --scenario ranking --report runs/ranking.md
```

默认仍是 `--retrieval literal`。单独安装索引依赖可用 `pip install '.[indexed]'`。
范围、解析限制、候选过期机制见 [索引分析说明](docs/indexed-analysis.md)。

## 真实模型

把 `.env.example` 复制为 `.env`，在本地填写供应商密钥、模型名和兼容接口地址，勿发送密钥到聊天中。

```dotenv
CODETRACE_API_KEY=本地填写
CODETRACE_BASE_URL=https://api.deepseek.com
CODETRACE_MODEL=deepseek-chat
```

接口地址和模型名以供应商当前文档为准。运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --question "main 如何调用 greet？请读取相关代码并引用。" --trace-dir runs
```

配置只从调用者当前目录的 .env 读取，不主动加载目标仓库配置。真实模式会将读取内容发送到配置的模型接口，只分析有权发送的代码。模型需支持 tools；最终结构JSON由程序校验，不依赖供应商专属结构化输出接口。

## 预算与结果

默认最多8次模型请求（含修正）、16次工具调用、90秒单轮模型超时、180秒任务时限、60000输入字符。可用 `--max-rounds`、`--max-tools`、`--timeout`、`--max-context-chars` 调整。输入字符不是精确token计费上限；usage只使用服务端值，缺失保持null。

completed 表示结构与证据范围通过，不代表人工语义评分通过。insufficient_evidence 明确无法确认，但属于正常响应；两者退出码0。运行失败/校验失败/预算终止为1，参数/配置/记录写入错误为2。

`--trace-dir runs` 显式保存 schema_version=1 的JSON，包含消息、源码证据、工具参数、耗时及停止原因。默认不保存；records 不含配置密钥或供应商异常正文。记录包含源码，请自行控制分享范围。runs 已被Git忽略。新协议不再把无引用自由文本判定为 completed。

`--report PATH` 纯渲染 Markdown，不增加模型调用。**报告和 trace 必须在被分析仓库外**，含链接/reparse父目录的输出路径也拒绝。分析自身时用 `--repo . --trace-dir ../codetrace-runs --report ../codetrace-runs/self.md`。

## 评测与面试准备

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace.evaluation
```

默认运行 Python/Java 共10题固定离线回归，覆盖入口、跨文件、配置、异常和无答案。仓库哈希及源码标注不符会拒绝评测。报告将文件覆盖、引用校验与人工语义评分分开；真实模型需要显式 `--live`，当前尚未验收。操作和评分格式见 [评测说明](docs/EVALUATION.md)，讲解线索见 [面试准备](docs/INTERVIEW.md)。

新增v2基准包含Petclinic、Flask、mall-tiny固定提交，24题×literal/indexed共48个组合。
默认offline，每次最多4个组合；无外部源码时保留not_run，不自动下载。真实执行、续跑、
保留集冻结与人工审核见 [成对评测](docs/paired-evaluation.md) 和 [基准准备](benchmarks/README.md)。
75%是后续编程阶段的建议门槛，不是当前成绩；当前 `analysis_ready_for_programming=false`。

## 源码阅读与限制

1. `src/codetrace/graph.py`：状态、节点与条件路由。
2. `repository.py`：访问边界、扫描预算及工具定义。
3. `contracts.py` / `evidence.py`：严格契约、快照与引用校验。
4. `models.py` / `cli.py` / `records.py`：模型、命令入口及记录。
5. `indexing.py` / `symbols.py` / `retrieval.py`：内容快照、静态导航和词法排名。
6. `tool_registry.py` / `benchmark.py` / `paired_evaluation.py`：按任务工具权限、固定基准及对照协议。

详细说明见 [架构](docs/ARCHITECTURE.md)、[工具](docs/TOOLS.md)、[结果协议](docs/RESULTS.md)、[验收记录](docs/VERIFICATION.md)。

路径检查拒绝链接/reparse和常见凭证文件名，但不是OS安全沙盒，不能防御恶意进程同时更改仓库，也不能发现所有普通源码内密钥。总时限停止后不再调度请求，不保证硬取消正在阻塞的文件读取。重复检测采用有界内容指纹，面向小仓库；不宣称全程序调用关系分析。

本项目未添加发布许可证。工作区 backup 是独立的旧项目，外层早期设计文档不代表当前实现。
