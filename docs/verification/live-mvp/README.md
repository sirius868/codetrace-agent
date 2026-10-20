# 旧MVP真实验收记录

模型：qwen3.8-27b；日期：2026-10-20；所有原始usage保留，费用未知。

| Smoke | Stop | 模型请求 | 工具 | 耗时ms | tokens |
|---|---|---:|---:|---:|---:|
| entry | completed | 3 | 4 | 12064.16 | 4186 |
| cross-file | completed | 3 | 4 | 34015.54 | 5583 |
| config | completed | 6 | 11 | 45834.54 | 11913 |
| no-answer | completed | 4 | 6 | 29871.52 | 6427 |

助手核对（非human审核）：入口与跨文件回答的主要调用关系符合源码；配置回答定位TIMEOUT_SECONDS=30正确，但未确认事项中“未命中即视为不存在”的表述过强；no-answer输出completed，同时承认无法确认特性语义，不能作为正确不足回答的成功证据。

十题真实报告：ten-case/e840b4b513ac4eedb8b92ffeaa87a914/report.json。8个completed、2个insufficient_evidence；这是结构状态计数，不是语义成功率。

助手草稿发现python-exception把CodeTrace长度写成10（实际9）。其他题的初步判断仍需人工核对。
ten-case-assistant-draft.json未导入v1评分器，因此reviewed仍为0、live_success_rate为null。
人工应逐题阅读答案、预期事实及引用，修正草稿，明确确认后才能按EVALUATION.md生成正式v1审核文件。
旧6.3四场景已执行并记录成功/失败；旧6.4及新9.2因缺人工审核保持待验收。
