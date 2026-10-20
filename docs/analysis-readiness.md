# 分析阶段验收与编程路线图

变更：strengthen-codetrace-repository-analysis。当前分析工具与离线回归已实施，
真实成对运行和人工验收仍在进行；`analysis_ready_for_programming=false`。

## 已有工程证据

- 独立 `.venv-verify` / Windows 11 / Python 3.12.10：137 passed、1 skipped，pip check通过。
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
当前Pro独立报告位于`runs/paired/pro-live.json`；三种模型结果互不混算。
当前没有全量人工语义成绩，也没有“indexed优于literal”的结论。

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
