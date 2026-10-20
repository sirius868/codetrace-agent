# 索引分析与报告

PowerShell，在 CodeTrace 根目录安装依赖并执行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m codetrace --repo examples/demo_repo --offline --retrieval indexed --scenario navigation --trace-dir runs/indexed --report runs/navigation.md
.venv\Scripts\python.exe -m codetrace --repo examples/demo_repo --offline --retrieval indexed --scenario ranking --report runs/ranking.md
```

两个演示使用固定步骤，只验证导航/排序→读取→引用→报告，不解释任意问题，也不需要Key。
真实模式去掉 --offline，使用 --question。解析器缺失时 indexed 明确报配置错误，literal仍可使用。

兼容变化：--trace-dir 和 --report 必须位于被分析仓库之外，路径含链接或reparse父目录也拒绝。
分析 CodeTrace 自身时用 `--repo . --trace-dir ../codetrace-runs --report ../codetrace-runs/self.md`。
上述 examples/demo_repo 示例可以写 runs，因为它在被分析子仓库之外。
输出预检在模型运行前执行，错误退出2；写入使用临时文件和原子替换，失败保留原文件。
报告由已记录Result纯渲染，不产生额外模型调用；费用/usage缺失显示未知。

Result仍为schema_version=1。trace新增retrieval_setup和工具retrieval事件，包含模式、
解析器/算法版本、预算、候选及计时。不应将引用结构校验当作答案语义正确。
原literal仍会对重复调用计算有界全仓库指纹；相关IO包含在工具耗时中，尚未声称性能提升。

完整离线导出示例：verification/indexed-navigation.md。
