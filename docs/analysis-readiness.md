# 分析阶段验收与编程路线图

变更：strengthen-codetrace-repository-analysis。当前分析工具与离线回归已实施，
Pro真实开发集已运行，保留集因当时供应商403未运行；随后切换Qwen Max，人工验收待完成；`analysis_ready_for_programming=false`。

## 已有工程证据

- 独立 `.venv-verify` / Windows 11 / Python 3.12.10：最终全量141 passed、1 skipped，pip check通过。原始输出及环境记录见 verification/analysis-upgrade/final-checks.json 与 final-pytest.txt。
- literal四演示、indexed导航/排名演示、Markdown导出、v1离线和v2缺仓库命令全部退出0。
- 原始输出位于 verification/analysis-upgrade/。真实符号链接集成因Windows权限跳过，属性拒绝测试通过。
- CI配置覆盖Windows/Linux，不调用真实模型或下载外部源码；Linux与远程Actions尚未运行。
- 基准为三个固定仓库24题，全部路径/范围/哈希验证通过；标注仍为助手草稿，非人工签署。

## 真实验收

旧MVP四场景与十题报告见 [真实记录](verification/live-mvp/README.md)。
四场景均有真实结果，包含拒答状态及表述问题；十题已运行，人工审核0。
8个completed、2个insufficient_evidence不是80%或100%语义成功率。

v2完整计划为48个组合。用户中途要求切换模型：Qwen的15个完整组合保留在本地
`runs/paired/live.json`，中断时在途任务usage未知，不编造为零。已观察到Petclinic入口题
两模式context_budget；不得删题或提高预算后混算。停止摘要见 verification/qwen-interrupted.json。

通过原接口模型列表确认正确ID为`deepseek-v4.1-flash`，连通记录见verification/model-switch.json。
最初按用户连写名称`deepseekv4.1flash`请求返回404，修正为接口实际ID后成功；未变更Key或Base URL。
Flash开发集报告位于`runs/paired/deepseek-live.json`：32个开发组合已执行，最后10个组合为
PermissionDeniedError，保留题未运行。摘要见verification/flash-development-summary.json。
随后用户要求切换`deepseek-v4-pro-0813`，接口连通通过（verification/pro-model-switch.json）。
Pro独立报告已保存到 [原始报告](verification/pro-paired/report.json) 与
[逐题审核材料](verification/pro-paired/review-packet.md)，三种模型结果互不混算。
Pro开发集32个组合均已执行，literal与indexed各8个completed、8个失败；没有人工语义成绩。
其中literal的一个completed属于无答案题且状态不符合拒答契约，不能据此计成功。
最后4个组合为PermissionDeniedError；最小请求复查确认HTTP 403、AllocationQuota.FreeTierOnly，
见 [接口复查](verification/pro-connectivity-recheck.json)。保留集16个组合全部not_run，尚未生成freeze。
当前冻结配置下即使indexed所有completed及8个未运行题均正确，最多16/24，也低于18/24门槛；
这是按停止状态得到的理论上限，不是实测成功率。恢复权限并完成剩余评测仍有验收价值，
但本轮不能宣称达标；后续改进需新实验，不能挑选重试结果或混用模型。
当前没有全量人工语义成绩，也没有“indexed优于literal”的结论。

用户随后改为`qwen3.8-max`，保留原Key及DashScope地址；最小连通请求成功，
见 [Qwen Max连通记录](verification/qwen-max-model-switch.json)。模型切换不会改变Pro报告，
Qwen Max尚无完整48组合评测，不能沿用Pro的32个组合续算同一实验。
真实indexed跨文件smoke已完成：4次模型调用、6次工具、completed，
见 [执行原始记录](verification/qwen-max-smoke.json) 和 [分析报告](verification/qwen-max-smoke.md)。
回答的main→greet、静态返回值及脚本入口与示例源码一致；仅为单例助手核对，非人工验收成绩。

## 当前阻塞与继续方式

1. Pro报告保留历史403及未运行项；若需要恢复Pro对照，在供应商控制台核查免费额度和调用权限，不自动修改计费选项。
2. 当前Qwen Max已通过最小连通检查，后续正式对照须新建报告。模型/预算/源码/提示改变均不能续用旧配置的成绩。
3. 完成开发结果人工分类，冻结配置后执行保留集；保留已有失败attempt，显式重试必须另记历史。
4. 审核原MVP十题及本次全部结果。现有32条assistant_draft已逐题绑定身份，不能当作human导入成绩。

OpenSpec 9.2、9.3、9.4、9.5仍未完成。本次交付代码和真实失败记录，不归档变更，
不以权限阻塞或测试通过代替人工验收。详细问题见 [失败复盘](verification/pro-paired/README.md)。

## 人工验收标准

所有24题×2模式真实执行并human审核后，才可计算完整成功率。
indexed整体至少18/24、保留集至少6/8、语义成功数不低于literal，且无已知未修复的
只读边界/引用回归，方可将ready改为true。assistant_draft不能满足该门槛。
功能实施与质量达标分开记录；失败报告是有效交付，但不会自动变成编程阶段批准。

## 后续路线（尚未实施）

1. 分析结果生成修改建议：目标文件、证据、约束、验证方案，供人工审阅。
2. 在独立工作区支持一种有限补丁任务，例如参数校验及对应测试，明确可修改范围与回退。
3. 在限定环境执行预定测试，使用有限次数反馈修正，输出diff与测试记录。

以上必须另起propose/apply，当前没有写入目标源码、Shell执行、自动补丁或自动部署能力。
在当前失败类型和人工审核完成前，建议继续完善分析定位、上下文使用及不足回答一致性。
