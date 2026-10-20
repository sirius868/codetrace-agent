# 仓库工具契约

所有工具接收 `/` 分隔的仓库相对路径，共用路径校验与有界遍历，不执行被分析源码。拒绝父目录穿越、绝对路径、符号链接和 Windows reparse point。普通源码中的秘密不一定能被文件名规则识别。

| 工具 | 默认值及范围 | 结果 |
|---|---|---|
| repository_overview | path='.'，最多500文件 | file_count、by_suffix、directories、candidate_paths；统计只覆盖本次可访问文件 |
| list_files | path='.'，limit=100，上限500，可选suffixes列表 | files、scanned_entries、skipped_entries、skip_reasons、truncated、truncation_reasons |
| search_code | query必填，path可为文件或目录，limit=30上限100，context=0至3，可选suffixes | matches带真实行号及上下文；跳过原因和截断原因明确返回 |
| read_file | start=1，end省略取start+79，最多120行 | lines、start/end、sha256、next_start、eof、truncated；空文件行范围为null |

每次遍历最多10000目录项，读取文件最多256000字节，返回片段最多12000字符。字符预算截断只发生在完整行边界；单行超过预算返回 line_too_long。搜索行及上下文每行最多500字符并标注截断。文件扫描未耗尽目录项预算时使用稳定排序；被截断的遍历不承诺全量结果。搜索摘要不能直接作为最终引用证据。

例：`search_code(query='greet', path='service.py', context=1)`；`search_code(query='main', suffixes=['.java'])`；`read_file(path='long.py', start=121)`。工具均返回 ok/data 或 ok/error，错误码区分参数、路径、编码和文件访问问题。

## indexed 模式

`--retrieval indexed` 增加以下工具；默认 literal 仍只开放原四个工具。

| 工具 | 参数 | 返回 |
|---|---|---|
| find_symbol | name 1～200字符；kind/language/path可选；limit默认10，最多20 | exact优先、prefix明确标注；限定名、种类、签名、行号、sha256、symbol_id |
| find_related_symbols | symbol_id、relation必填；limit默认10，最多20 | extends/implements/extended_by/implemented_by；原始声明、候选目标、resolved/ambiguous/unresolved |
| search_code_ranked | query 1～200字符；path/suffixes可选；top_k默认5，最多20 | BM25、符号/路径加分、源码范围、版本、摘要和截断标记 |

示例：`find_symbol(name='OwnerController', language='java')`；取得 symbol_id 后调用
`find_related_symbols(symbol_id='返回的ID', relation='implements')`；
`search_code_ranked(query='TIMEOUT_SECONDS', suffixes=['.properties', '.py'])`。
所有导航结果必须再调用 read_file 才能引用，symbol_id 不是 evidence_id。

索引懒构建，只在一次分析任务内复用。默认最多2000文件、10000目录项、单文件256000字节、
累计16MiB原始读取（包含解码失败和过期文件刷新）。无法在剩余预算确认EOF时跳过该文件，
不索引截断文本。候选复核按查询去重且另记validation_bytes。额外排除target、虚拟环境变体。
返回diagnostics说明partial、跳过类别、解析状态、读取字节、构建与查询时间、清单摘要。
每次返回候选前复核文件哈希，变化/删除/拒绝访问返回index_stale；下次查询刷新受影响文件。
新增文件需新任务重新发现；原read_file证据仍绑定旧快照。索引ID区分任务，清单摘要区分内容。
任务时限覆盖索引构建，协作取消会停止后续扫描；不保证硬取消OS文件读取线程。

Java用Tree-sitter解析，Python用ast。语法错误整文件禁用符号、保留文本检索。
提取词法定义、导入、注解、显式基类。通配导入保留歧义，外部/动态类型可能unresolved；
不解析Spring注入、Lombok、运行调用图或泛型绑定。签名与每条线索最多300字符，导入/注解各最多10条。

排名规则v1：80行片段、20行重叠、最多8000字符（整行）；超长行跳过并记录。
保留完整标识符，拆camel/snake，中文二元片段；BM25 k1=1.2、b=0.75，完整符号名匹配+3、
完整查询在路径中匹配+1。只返回正分，按分数降序及路径/行号升序稳定排序。
每摘要最多400字符、总摘要最多4000字符。中文概念与源码无共同词项时可能无结果，没有embedding语义翻译。
`tests/test_retrieval.py` 的同候选集合组件测试中两个正例Recall@5均为1，中文负例均无命中；
这只验证排序组件，不是陌生仓库Agent成功率，也不证明新模式优于旧模式。
