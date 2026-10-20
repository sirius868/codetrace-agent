# CodeTrace 对话交接文档

更新日期：2026-10-20。替换早期MVP交接记录，供用户及下一次对话继续开发。
交接基线提交：`1b7198b`；本文件以独立文档提交保存。事实以源码、原始报告和最新任务状态为准。

## 1. 用户目标及已确定的方向

- 用户是211软件工程大三学生，Java基础及后端技能正在学习，Python基础够用；求职AI Agent/LLM应用实习，同时保留Java后端方向。
- 用户做两个独立项目：已有Java后端项目，CodeTrace作为独立Python Agent项目。不要为了堆技术而拆Java/Python微服务。
- 最初选择OpenManus，随后明确选择重新创建基于LangGraph的项目。当前CodeTrace不是旧项目执行循环的迁移版本。
- 名称为知码 · CodeTrace，产品方向是代码仓库分析助手。先完善分析Agent；编程Agent只保留路线图，须另起提案。
- 偏好动手、低成本国内模型API、可运行可测试的工程成果。不能把官方示例或离线模拟包装成自主分析成绩。
- 最新模型要求是`qwen3.8-max`。本次最后请求为输出对话交接文档，不是启动新一轮完整付费评测。

## 2. 工作区与操作约束

| 项目 | 当前值 |
| --- | --- |
| 项目根目录 | `D:\_Workspace_\ai_agent\codetrace-agent` |
| 外部基准 | `D:\_Workspace_\ai_agent\codetrace-benchmarks` |
| 旧项目备份 | `D:\_Workspace_\ai_agent\backup`，本阶段未修改 |
| 环境 | Windows PowerShell，Python 3.12.10，LangGraph 1.2.16 |
| 虚拟环境 | `.venv`用于开发；`.venv-verify`用于独立验证 |
| Git | `main`；https://github.com/sirius868/codetrace-agent.git |

最近实现与评测提交保存在本地，`1b7198b`尚未推送；不要把此前的一次push授权理解成之后自动push。
[AGENTS.md](../AGENTS.md)要求改动更新相关测试并创建Git提交。PowerShell须检查`$LASTEXITCODE`，不能测试失败后继续提交。

交接时须保留的用户改动：

- README开头删去旧OpenManus备份说明，标题改为“已实现功能”；这两处仍未暂存。
- 未跟踪的`.agents/`、`openspec/config.yaml`、`openspec/changes/archive/`、`openspec/specs/`。

不要批量`git add .`或重置这些内容。CodeTrace未添加发布许可证；基准源码摘录的
[上游许可证声明](../benchmarks/upstream-notices.md)须保留，它不是CodeTrace自身许可证。
当前不需要多Agent、Web、向量数据库、目标代码执行、自动克隆或持久化会话恢复。

## 3. 当前模型及秘密处理

本地被Git忽略的`.env`已配置：

```dotenv
CODETRACE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CODETRACE_MODEL=qwen3.8-max
```

继续使用原有本地Key。本文件不含Key；不要从旧聊天复制Key，不打印`.env`全文，不把秘密写入报告或提交。
配置从运行命令的当前目录读取，不加载被分析仓库的环境文件。

[最小连通检查](verification/qwen-max-model-switch.json)成功，返回模型ID一致。
[真实indexed执行记录](verification/qwen-max-smoke.json)完成4次模型调用、6次工具调用，
run_id为`25b201cddbb5490aae0007a1e8f303d9`，状态completed，耗时53637.82ms。
[分析报告](verification/qwen-max-smoke.md)解释了main→greet、静态返回值及脚本入口。
助手已核对示例源码，但这是单例验证，不是完整能力成绩或人工验收。

历史顺序：qwen3.8-27b → deepseek-v4.1-flash → deepseek-v4-pro-0813 → qwen3.8-max。
用户最初连写的`deepseekv4.1flash`曾返回404，实际从模型列表确认的ID是`deepseek-v4.1-flash`。
当前Qwen Max连通成功，不能把Pro历史403说成当前模型也不可用，也不保证后续额度一直可用。

## 4. 已实现能力与源码入口

| 能力 | 实现及边界 |
| --- | --- |
| 分析闭环 | `graph.py`：model/tools/validate/repair四节点；修正最多一次且禁用工具 |
| 基础探索 | `repository.py`：概览、列表、字面量搜索、按行读取；路径、凭证、链接/reparse、编码及扫描预算保护 |
| 证据校验 | `contracts.py`、`evidence.py`：read_file快照、SHA-256、任务内evidence_id及严格引用范围；合法引用不证明语义正确 |
| 任务索引 | `indexing.py`：懒构建、2000文件/10000目录项/单文件256000字节/累计16MiB；候选哈希复核、index_stale与下次刷新 |
| 静态导航 | `parsing.py`、`symbols.py`、`indexed_tools.py`：Java Tree-sitter、Python AST；定义、嵌套、重载、有限继承关系；保留歧义，不模拟Spring运行时绑定 |
| 排名检索 | `retrieval.py`：BM25 v1，k1=1.2、b=0.75；标识符拆分、中文二元片段；80行块/20行重叠，无embedding语义检索 |
| 工具权限 | `tool_registry.py`：literal四工具；indexed增加find_symbol、find_related_symbols、search_code_ranked；导航ID不能引用 |
| 输出 | `reporting.py`、`records.py`：原子JSON/Markdown；报告与trace必须在被分析仓库外 |
| 评测 | `evaluation.py`保留v1；`benchmark.py`、`paired_evaluation.py`实现v2固定源码、成对运行、分批续跑、attempt历史与人工审核 |

默认literal，indexed显式启用。解析依赖tree-sitter==0.25.2、tree-sitter-java==0.23.5，开发快照已包含。
默认每任务8次模型请求、16次工具调用、180秒总时限、90秒模型时限、60000输入字符。
适配器固定max_tokens=2048，SDK最多重试1次；费用未知，不编造计价。
协作取消不能硬取消OS文件读取；路径检查不是防恶意并发文件替换的OS沙盒。

详见[架构](ARCHITECTURE.md)、[工具](TOOLS.md)、[索引说明](indexed-analysis.md)、[成对评测](paired-evaluation.md)、[面试讲解](INTERVIEW.md)。

## 5. 实际验证及评测状态

### 工程验证

- 最近完整独立环境测试：**141 passed、1 skipped**，100.22秒；[原始输出](verification/analysis-upgrade/final-pytest.txt)。
- 跳过的是Windows创建真实符号链接权限测试，模拟链接/reparse拒绝测试通过；不能把跳过写成通过。
- pip check通过；[结果清单](verification/analysis-upgrade/final-checks.json)。
- 加入最终Qwen Max记录校验后，`tests/test_upgrade_delivery.py`的4项测试通过。
- literal四场景、indexed两场景、报告导出、v1离线和v2缺仓库评测均已实际执行。
- CI覆盖Windows/Linux；远程Actions和Linux实际运行尚未核实。
- OpenSpec严格校验及差异检查通过。交接文档新增校验单独运行，不混写成上述历史全量测试。

### 真实运行

| 实验 | 实际进展 | 证据与限制 |
| --- | --- | --- |
| 旧MVP Qwen | 四场景及固定10题已执行；8 completed、2 insufficient | [记录](verification/live-mvp/README.md)；人工审核0，存在真实语义错误 |
| v2 Qwen 27b | 换模型前保存15个完整组合 | [中断摘要](verification/qwen-interrupted.json)；在途usage未知 |
| v2 DeepSeek Flash | 32个开发组合；最后10个权限失败 | [摘要](verification/flash-development-summary.json)；保留集未运行 |
| v2 DeepSeek Pro | 32个开发组合，两模式各8 completed、8失败；最后4个权限失败 | [原始报告](verification/pro-paired/report.json)、[逐题审核](verification/pro-paired/review-packet.md)、[复盘](verification/pro-paired/README.md) |
| 当前Qwen Max | 最小连通及一次indexed跨文件smoke成功 | 没有完整48组合成绩，不能续接其他模型报告 |

Pro最小复查返回HTTP403、AllocationQuota.FreeTierOnly，见[接口记录](verification/pro-connectivity-recheck.json)。
只确认免费额度相关限制，未确认具体耗尽、开关或授权，不断言欠费，也未替用户改计费设置。
Pro的16个保留组合全部not_run，**尚未生成freeze或执行保留集**。
32条审核意见是assistant_draft，不是human；语义成功率保持null。
按现有停止状态，Pro indexed即使8个completed和8个未运行题全部正确，最多16/24，低于18/24门槛。
这是理论上限，不是实测成功率；completed中仍可能有事实遗漏或错误。

### 固定基准

| 仓库 | 提交 | 分组 |
| --- | --- | --- |
| spring-projects/spring-petclinic | `500158f732419217507c7656904b8e6aa1bcc0d6` | 开发，8题 |
| pallets/flask | `d086db856be187255b8ec61ef409357393020f32` | 开发，8题 |
| macrozheng/mall-tiny | `a81ec4740a0c7c99a06ebffb43a14168beadffc3` | 保留，8题 |

数据为[repository-analysis-v2.json](../benchmarks/repository-analysis-v2.json)，路径见[repo-map.example.json](../benchmarks/repo-map.example.json)。
24题×两模式=48个组合，默认每批4任务。失败与未运行不能从分母删除，gold只用于事后评分。
续跑核对源码、数据、模型、提示、工具、预算摘要；换模型必须新报告，不能混算或挑最好attempt。
保留集须在开发阶段结束并写入freeze后首次运行。若根据其结果调优，新的未见效果验证须换独立保留仓库。
本地旧报告为`runs/paired/live.json`、`deepseek-live.json`、`pro-live.json`；runs被忽略，Pro副本已提交，前两者只提交摘要。

## 6. OpenSpec剩余工作

- deliver-codetrace-analysis-mvp：**27/28**，6.3已完成，6.4仍缺真实十题人工审核。
- strengthen-codetrace-repository-analysis：**33/37**，功能、测试、文档集成已实施，9.2/9.3/9.4/9.5未完成。
- 均未归档；当前`analysis_ready_for_programming=false`。

| 任务 | 仍需完成 |
| --- | --- |
| 9.2 | 原MVP固定10题人工审核，不能用新评测替代 |
| 9.3 | 开发集成对结果的人工失败分类；Pro已有运行及草稿，未获人类确认 |
| 9.4 | 开发结束后冻结配置，执行保留集两模式并保留全部attempt |
| 9.5 | 全部至少48个结果人工审核，交付完整对照及达标/未达标判断 |

人工审核绑定report_id、dataset_sha256、case_id、variant、run_id；不能批量把assistant_draft改成human冒充审核。
进入编程阶段的建议门槛：全部48组合真实执行并审核；indexed整体≥18/24、保留≥6/8；成功数不低于literal；无已知未修复的只读/引用回归。
失败报告可以交付，但不能放宽标准或声称已具备编程能力。

显式继续OpenSpec时先读取对应`.agents/skills/openspec-apply-change/SKILL.md`并获取最新instructions。
修改任务须核对返回sourcePath和行号处的原描述，完全完成才勾选并复查；不要凭交接文档批量勾选。

## 7. 已知问题与接手优先级

1. **取证与预算**：Flask session题多次读取超过120行，返回invalid_range并耗尽轮次；另一模式读大片段导致上下文超限。优先研究参数提示、按符号精读及停止取证策略。
2. **输出预算**：Pro就诊题修正请求2048个completion token全部为reasoning，未生成合法结构。可能需要可配置输出预算；未保存finish_reason，不能把原因说成已完全证实。
3. **拒答状态**：文字承认无法确认线上事实，却返回sufficient/completed，违反无答案契约。
4. **语义错误与遗漏**：Flask session执行顺序描述错误，JpaRepository继承与ensure_sync调用等预期事实遗漏；引用有效不能替代事实审核。

建议先阅读失败复盘并审核代表案例，再确定新改进范围。若以Qwen Max正式对照，从新报告的开发集开始，按批执行。
不要因换模型就无说明重跑48项；不要重装已验证环境、重新克隆项目，或优先扩Web/编程工具。

## 8. 接手命令

```powershell
Set-Location D:\_Workspace_\ai_agent\codetrace-agent
git status --short
openspec instructions apply --change strengthen-codetrace-repository-analysis --json

# 离线导航，不调用模型
.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --offline --retrieval indexed --scenario navigation --report runs/navigation.md

# 当前Qwen Max真实调用
.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/demo_repo --retrieval indexed --question "main 如何调用 greet？请读取相关代码并引用。" --report runs/qwen-max-example.md

# 决定继续正式对照后使用新文件，默认最多4个任务
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --live --repo-map benchmarks/repo-map.example.json --output runs/paired/qwen-max-live.json --max-runs 4

# 仅在上述文件已生成且配置未变时续跑
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --live --repo-map benchmarks/repo-map.example.json --resume runs/paired/qwen-max-live.json --output runs/paired/qwen-max-live.json --max-runs 4
```

完整回归：`.venv-verify\Scripts\python.exe -m pytest -q -rs`与`-m pip check`。
交接时没有本对话遗留的评测进程需要等待。`runs/analysis-upgrade/`内临时脚本被Git忽略，不要无检查直接运行旧模型批处理或保留集脚本。

## 9. 可粘贴给下一次对话

> 请先阅读 `D:\_Workspace_\ai_agent\codetrace-agent\docs\HANDOFF.md`，核对Git及OpenSpec状态。
> CodeTrace是独立Python/LangGraph只读仓库分析Agent，当前qwen3.8-max已验证工具调用；Key留在本地。
> 分析增强已实施，OpenSpec为33/37，尚缺人工验收与保留集执行。Pro结果不能与Qwen Max混算。
> 保留README两处用户改动和原有未跟踪配置，不自动push、归档、扩编程能力或重跑完整付费评测。
> 先说明最值得处理的真实失败，再按我接下来的具体任务继续。
