# CodeTrace 分析报告

本报告展示程序结果和引用校验，不代表人工确认语义正确。

## 问题

定位 main 定义。

## 状态

- run_id: 61b88fa5fead42e9a7c5971be5b282ad
- 停止原因: completed
- 证据状态: sufficient
- 运行模式: offline

## 事实与引用

- 离线演示读取了该源码片段（不是模型语义推理）。
  - app.py:L1-L10 (61b88fa5fead42e9a7c5971be5b282ad:1)

## 未确认事项

本次输出未列出额外事项；这不证明分析覆盖完整。

## 证据快照

- app.py:L1-L10; SHA-256 b07fe549eef088acad3e34775654124202fe980d920ee20a00e0b66a9d977a45; 61b88fa5fead42e9a7c5971be5b282ad:1

## 索引覆盖

检索模式: indexed
文件数: 3; partial: False; 累计构建读取字节: 256
清单摘要: f69b93090912ad4c368bd4242414da25f037f5ba36a9dbff15da4e35708291de

{"build_ms": 8.9, "config": {"max_entries": 10000, "max_file_bytes": 256000, "max_files": 2000, "max_total_bytes": 16777216}, "file_count": 3, "index_id": "63518ae98ec04b4dac2c93f31535f5eb", "manifest_sha256": "f69b93090912ad4c368bd4242414da25f037f5ba36a9dbff15da4e35708291de", "parse_states": {"parsed": 3}, "partial": false, "query_ms": 10.32, "read_bytes": 256, "scanned_entries": 3, "scope": "initial manifest; new files require a new task", "skip_reasons": {}, "truncation_reasons": \[\], "validation_bytes": 177}

## 执行统计

- 模型: DemoModel
- 模型请求: 3
- 工具执行: 2
- 修正次数: 0
- 总耗时毫秒: 73.85
- usage: 未知
- 费用: 未知（未配置可核实的供应商价格）
