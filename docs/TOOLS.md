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
