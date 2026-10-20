# Spec Delta

## Purpose

为 CodeTrace 提供可理解、可限制和可验证的本地源码访问能力，使用户能够在不运行目标程序的情况下定位文件与代码，并明确区分搜索未命中、访问失败和扫描不完整。

## ADDED Requirements

### Requirement: Read-only repository boundary
系统 SHALL 只读取用户指定根目录内的本地文件，拒绝绝对工具路径、父目录穿越、符号链接、Windows reparse point 及凭证排除路径；所有探索入口使用相同访问规则，不提供代码执行或写入目标仓库的工具。

#### Scenario: Reject escaping paths
- **WHEN** 请求读取 `../secret.py`、链接文件或链接目录中的文件
- **THEN** 返回结构化访问错误，不返回目标内容，仓库内容不改变

#### Scenario: Exclusions apply across tools
- **WHEN** 列目录、概览或搜索经过 `.git`、`.venv`、`node_modules`、`.env` 或私钥排除路径
- **THEN** 不返回其中内容，直接读取这些路径同样被拒绝

### Requirement: Bounded repository overview
系统 SHALL 提供 `repository_overview`，返回有界扫描下的源码文件总数、按后缀统计、主要目录及 README/构建文件候选路径，并提供扫描数量、跳过数量、截断标记及原因；扫描未完成时不得把统计宣称为全仓库精确总数。

#### Scenario: Summarize Python and Java fixtures
- **WHEN** 概览完整扫描一个含 Python、Java、README 和构建文件的小仓库
- **THEN** 统计与实际可访问文件一致，候选路径存在，结果明确候选不代表已解析调用关系

#### Scenario: Traversal budget reached
- **WHEN** 扫描达到目录项或文件数量预算
- **THEN** 返回已有结果并标记 `truncated=true` 和对应原因，而不是报告完整扫描

### Requirement: Scoped literal search
系统 SHALL 保留 `search_code` 并支持单文件或目录范围、可选后缀过滤及最多三行的匹配前后文。搜索为区分大小写的字面量匹配，结果带文件、行号和截断原因；相同静态目录及参数在预算内返回稳定顺序。

#### Scenario: Search one file with context
- **WHEN** 在 `service.py` 搜索存在的函数名并请求前后各一行
- **THEN** 仅返回该文件命中，匹配行号与上下文行号准确且不超出文件边界

#### Scenario: Narrow a truncated search
- **WHEN** 全仓库搜索达到预算后用户改为某子目录并过滤 `.java`
- **THEN** 新搜索限于该目录和后缀，继续报告自身扫描范围与是否截断

#### Scenario: No match is not absence proof
- **WHEN** 搜索无命中但存在不可解码、大文件或预算跳过项
- **THEN** 返回空匹配并保留跳过数与原因，不能声称已证明仓库没有对应功能

### Requirement: Evidence-ready paged reads
系统 SHALL 保留 `read_file` 的真实行号、UTF-8 检查和文件哈希，单次限制 256000 字节文件、120 行及12000字符；省略 end 时从 start 起最多读取80行。未到文件尾时提供 next_start，空文件返回明确空结果，不伪造可引用行。

#### Scenario: Continue after a high starting line
- **WHEN** 读取一个200行文件并仅指定 start=121
- **THEN** 返回121至200行，省略 end 不触发范围错误，并标记已到文件尾

#### Scenario: Character budget and empty file
- **WHEN** 可读文件的返回字符数触及上限或目标为空文件
- **THEN** 前者在完整行边界截断并返回 next_start，后者返回零行且不能成为有效行引用；单行超限返回明确错误

### Requirement: Stable tool result contract
所有仓库工具 SHALL 返回 `ok/data` 或 `ok/error`，区分不存在、参数错误、访问拒绝、文件过大、二进制、编码不支持和文件系统错误；布尔值不得作为整数限制接受。

#### Scenario: Malformed parameters
- **WHEN** 模型传入数组参数、负数限制、布尔起始行或未知参数
- **THEN** 返回结构化参数错误，分析进程不崩溃，错误可以被下一轮模型观察
