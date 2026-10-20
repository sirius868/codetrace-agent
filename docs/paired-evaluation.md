# 成对评测与人工审核

准备外部仓库见 benchmarks/README.md。v1的10题命令和Result schema_version=1保留；
v2数据/报告schema_version=2，与结果版本分开。

```powershell
# 默认offline，仅模拟概览和不足回答；不下载源码、不创建网络客户端。
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --repo-map benchmarks/repo-map.example.json --output runs/paired/offline.json
# 显式真实模式：默认最多4个case-mode组合；需要本地.env。
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --live --repo-map benchmarks/repo-map.example.json --output runs/paired/live.json
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --live --repo-map benchmarks/repo-map.example.json --resume runs/paired/live.json --output runs/paired/live.json
```

可加 `--case-id petclinic-entry`（可重复）和 `--variant literal|indexed|both`、`--max-runs 4`。
未运行项留在48个计划分母中；缺仓库/配置有not_run_reason。失败组合默认不重跑，
`--retry-failed`明确重试，保留所有attempt、usage、失败，汇总采用最新attempt，不挑最佳成绩。
每题结束原子保存。恢复要求数据、源码内容、模型非秘密配置、预算、工具/提示/程序摘要一致。
更换模型、预算或实现必须开新报告，不能拼成一份可比成绩。

开发集结束后生成freeze JSON，至少包含当前报告configuration_sha256、code_commit、
dataset_sha256、frozen_at、held_out_used_for_tuning=false。冻结后运行保留集时传`--freeze PATH`，
配置摘要不符则拒绝；无freeze时保留题保持not_run。冻结不能靠事后补文件伪称首次验证。

审核文件是数组，每条示例：

```json
[{"report_id":"实际报告ID","dataset_sha256":"实际数据摘要","case_id":"petclinic-entry",
  "variant":"indexed","run_id":"当前attempt的实际run_id","reviewer":"审核者姓名",
  "review_source":"human","semantic_correct":true,"omitted_facts":[],
  "reasonable_refusal":null,"failure_category":"none","notes":"逐项核对事实和引用后的说明"}]
```

```powershell
.venv\Scripts\python.exe -X utf8 -m codetrace.paired_evaluation --resume runs/paired/live.json --review runs/paired/human-review.json --output runs/paired/reviewed.json
```

failure_category可为none/retrieval_miss/explanation_error/insufficient/model_error/budget_stop。
助手辅助审核必须写assistant_draft，不计reviewed；人工需逐项确认正确事实、遗漏、合理拒答。
导入校验report/dataset/case/variant/run身份，旧attempt审核不能误用于重试结果。

报告分别记录文件组覆盖、范围覆盖、引用合法性、人工语义、延迟、调用和原始usage。
无引用不算100%，无usage/价格不填零。未全运行或未全审核时完整成功率为null。
引用合法但解释错误仍是语义失败；失败及未运行不从分母移除。
literal/indexed同时改变工具集和检索范围，是整体方案对照，不据此宣称BM25因果收益。

analysis_ready_for_programming要求全部至少48个组合真实执行且human审核，indexed整体与
保留集至少75%，成功数不低于literal，边界/引用回归检查通过。未满足时保持false。
费用未知；小样本耗时中位数/最大值不是SLA或统计显著性。编程阶段仍需独立提案。
