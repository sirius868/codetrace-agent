# 业务评测

数据集为 `examples/evaluation.json`，两个只读小仓库各5题：入口、跨文件、配置、异常、无答案。不需要启动 Java 或 Python 样例。每题包含预期事实、文件、精确源码片段和仓库清单哈希。修改夹具后必须重新审核标注并更新哈希；校验失败不能继续生成可比成绩。清单覆盖夹具所有文件（排除 Python 字节码），统一 CRLF/LF 后计算 SHA-256，便于跨平台复现。

## 默认离线

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace.evaluation
# 安装包后也可用 .\.venv\Scripts\codetrace-eval.exe
```

离线使用标注中的文件及范围安排真实工具调用，最终文本明确只描述读取行为。它验证工具、状态图和记录，不能测试自主定位能力或语义推理。输出位于 `runs/evaluation/<report_id>/`，包含逐题原始记录、含逐题结果的 report.json 和摘要 report.md。例子见 `docs/evaluation-example/`，由实际运行保存，不能用于宣传模型成功率。

每题显示停止原因、有效引用文件覆盖、引用有效率、模型次数、工具数、耗时和原始 usage。文件覆盖按有效引用计算；无答案题没有预期文件，因此覆盖率为 null。无引用时引用有效率为 null。汇总输出分子、分母、measured 数及 case_errors；未产生结果的异常题不进入文件/引用分母，仍计入总题数和错误数。不得只引用汇总有效率而省略错误数量。usage_known_cases 表示有完整服务端 usage 的题数；不从字符数估算价格。

## 真实模型（未验收）

在调用者工作目录 `.env` 配置 CODETRACE_API_KEY、CODETRACE_BASE_URL、CODETRACE_MODEL 后：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace.evaluation --live --output runs/live-evaluation
```

只有显式 --live 才初始化模型客户端。缺失配置生成 not_run 报告并退出2，不能产生真实成绩。默认每题最多8次模型尝试、16次工具调用、180秒任务时限，调用量和预算保存在原始记录中。单题异常记录类型后继续下一题，不落盘供应商异常正文。配置和API本身的兼容性仍需实际验证。

## 人工审核

打开 report.json，逐题阅读 question、expected_facts、acceptable_uncertainties、result.findings 和源码证据，评估事实正确性、遗漏和拒答是否合理。不能根据引用范围合法直接勾选正确。创建 JSON（以下ID必须替换成对应报告实际值）：

```json
{
  "report_id": "对应报告ID",
  "dataset_sha256": "对应数据集哈希",
  "reviews": [{
    "id": "python-entry",
    "run_id": "该题任务ID",
    "semantic_correct": true,
    "omitted_facts": [],
    "reasonable_refusal": null,
    "notes": "逐项核对入口及输出行为后填写理由"
  }]
}
```

每条必须填写 semantic_correct、omitted_facts、reasonable_refusal 和 notes；无拒答时 reasonable_refusal 为 null。可分批审核，但只有真实模式的全部题均已审核才给 live_success_rate。有答案题还必须 completed 且无关键事实遗漏；无答案题必须 insufficient_evidence 且合理拒答。缺少人工评分的分母和 reviewed 数明确展示。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace.evaluation --report runs/live-evaluation/实际ID/report.json --review runs/review.json --output runs/reviewed
```

导入仅更新指定报告，不重新调用模型。report_id、dataset_sha256、每题 run_id 必须匹配；离线和真实模式的报告不能合并。首次真实验收需保留至少10题人工审核结果及失败案例。当前 live_status 为 not_run，没有真实语义成功率、提升比例或价格结论。
