# 验收记录

日期：2026-10-20。平台：Windows；Python 3.12.10；LangGraph 1.2.16。

本次 OpenSpec 变更：deliver-codetrace-analysis-mvp。离线可交付项已实施，真实模型验收保持待完成。

## 独立环境复现

实际新建 `.venv-verify`，与开发环境 `.venv` 分离，使用项目源码的 editable 安装：

```powershell
D:\Python\python.exe -m venv .venv-verify
.\.venv-verify\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv-verify\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv-verify\Scripts\python.exe -m pip check
.\.venv-verify\Scripts\python.exe -m pytest -q -rs
```

- 精确依赖快照安装、editable 构建均成功；已补充 setuptools==80.9.0，以支持无构建隔离安装。
- pip check：No broken requirements found。
- pytest：**75 passed, 1 skipped in 31.37s**。
- 跳过：`tests/test_repository.py:51`，Creating symlinks needs Windows developer mode or privileges。reparse/链接属性拒绝测试已执行；不能把真实链接集成测试写成通过。
- 开发期间新增断网测试曾因全局 socket 拦截影响 Windows asyncio 事件循环清理而报错；已限定拦截作用域，当前完整测试无该错误。
- 首次沙箱内 pip 下载被网络权限阻止；随后通过授权网络安装成功，未使用失败安装结果作为验收依据。

实际运行四个场景（均添加 `--trace-dir runs/clean-verification`）：

| scenario | stop_reason | 模型轮数 | 工具数 |
| --- | --- | ---: | ---: |
| entry | completed | 4 | 3 |
| cross-file | completed | 5 | 4 |
| config | completed | 4 | 3 |
| no-answer | insufficient_evidence | 3 | 2 |

全部为固定离线响应，无真实模型请求。cross-file 实际读取 app.py 和 service.py。对应记录在本地 runs/clean-verification（被 Git 忽略）。

运行 `.venv-verify/Scripts/codetrace-eval.exe --output runs/clean-evaluation` 成功，报告ID：`f4f5eec713114f0784334f6a3ca8d796`。10题中8题 completed、2题 insufficient_evidence。离线标注安排读取，不代表自主检索或推理能力。可追溯的已提交离线示例见 [report.md](evaluation-example/1de3d79ba9fd42a992af6456096f38b1/report.md)，该报告由开发环境实际运行生成，含全部逐题原始记录；测试已核对数据集哈希及记录一致性。

OpenSpec 严格校验通过。Windows/Linux Python 3.12 的 CI 已配置在 `.github/workflows/offline.yml`，配置契约测试通过。本地已执行对应安装、测试、演示与评测命令；**GitHub Actions 和 Linux 环境尚未实际运行，不能声称远程 CI 通过**。

## 待完成：真实模型验证

用户尚无 API Key，因此 tasks 6.3、6.4 保持未完成。没有真实模型调用量、费用、语义成功率或性能提升结论。HTTP mock 测试仅验证适配层协议；离线报告 live_status=not_run。

填写调用者工作目录 `.env` 后，使用下列真实 smoke 命令：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/eval_python --question "程序入口在哪里？给出代码引用。" --trace-dir runs/live-smoke
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/eval_python --question "main 如何调用 greet 并输出结果？请读取相关文件。" --trace-dir runs/live-smoke
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/eval_python --question "MAX_NAME_LENGTH 在哪里定义及使用？" --trace-dir runs/live-smoke
.\.venv\Scripts\python.exe -X utf8 -m codetrace --repo examples/eval_python --question "missing_feature_123 的数据库重试策略是什么？" --trace-dir runs/live-smoke
.\.venv\Scripts\python.exe -X utf8 -m codetrace.evaluation --live --output runs/live-evaluation
```

逐条审核真实答案，记录供应商/模型名、日期、usage、成功与失败案例；按 [EVALUATION.md](EVALUATION.md) 人工审核全部10题后再导入评分。完成两项在线验收才能勾选对应任务；当前变更未归档。
