# Spec Delta

## Purpose

为陌生仓库分析提供可限制、可核对的任务内源码视图，记录索引所覆盖的文件和版本。索引用于定位候选代码，沿用只读访问边界，并明确表示扫描截断、解析失败和源码变动，避免把局部结果当作完整仓库知识。

## ADDED Requirements

### Requirement: Bounded indexed source scope
索引 SHALL 复用既有仓库路径、链接、凭证和编码限制；仅读取用户指定本地根目录中的允许文件。默认上限为2000个文件、10000个扫描目录项、累计16MiB原始内容和256000字节单文件，构建时间计入同一任务时限；截断结果保留原因及已覆盖范围。

#### Scenario: Index budget exhausted
- **WHEN** 文件数、目录项数或累计字节任一达到上限
- **THEN** 停止进一步索引，返回已索引数量、实际读取字节数、跳过分类和 partial 状态，不宣称全仓库覆盖

#### Scenario: Forbidden files in index candidates
- **WHEN** 候选包含仓库外路径、链接、凭证文件或不支持的编码
- **THEN** 不返回被禁止文件内容；记录相应拒绝/跳过原因，新索引工具不绕开既有只读边界

#### Scenario: Deadline during index construction
- **WHEN** 索引构建期间耗尽任务剩余时限
- **THEN** 任务以 task_timeout 结束，不继续请求模型；仍遵守现有“不保证硬取消阻塞文件线程”的边界

### Requirement: Task-local index identity
每个索引 SHALL 记录独立 index_id、配置、仓库相对路径清单、逐文件SHA-256和覆盖摘要；不同任务不得共享可变索引状态。普通分析以有界内容清单标识版本，不强制仓库使用Git，不把内容哈希表述为Git提交号。

#### Scenario: Concurrent repositories with identical paths
- **WHEN** 两个任务同时分析均含 service.py 的不同根目录
- **THEN** 各自只返回对应仓库的符号、内容版本和索引ID，不发生路径同名导致的状态串用

#### Scenario: Reproducible static content
- **WHEN** 相同允许文件、内容和配置被重新索引
- **THEN** 覆盖清单及内容摘要可复现，运行实例ID可以不同，文件系统遍历的非业务顺序不改变完整扫描结果

### Requirement: Stale candidate detection
返回索引候选前系统 SHALL 核对涉及文件当前内容与索引哈希；发现变化、删除或权限改变时，不把旧范围当作当前位置返回。任务可以刷新受影响文件后重查，但新文件发现仅在显式重新构建清单或新任务时保证；此范围须向使用者说明。

#### Scenario: File edited after indexing
- **WHEN** 某方法定义在索引后移动到其他行
- **THEN** 返回结构化 index_stale 状态并使对应缓存失效，后续查询刷新该文件后返回新位置；旧任务已登记的证据仍绑定旧快照

#### Scenario: Candidate changes into a linked file
- **WHEN** 已索引文件在候选核对前被替换为链接
- **THEN** 重新应用链接拒绝规则，不返回链接目标内容，也不以旧索引片段作为新证据

### Requirement: Explicit parser coverage
索引 SHALL 区分文本已收录、符号解析成功、语法不支持和解析失败。单文件解析失败允许继续安全的文本检索，同时暴露解析状态；不得用不可靠的解析结果伪造准确符号关系。

#### Scenario: Syntax error in source
- **WHEN** 某 Java 或 Python 文件存在语法错误或解析器不支持的构造
- **THEN** 对该文件禁用不可信的符号结果，保留文本检索与读取能力，其他文件仍可正常索引
