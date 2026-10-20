# 分析能力扩展前的基线

manifest.json 固定扩展前提交和源文件 SHA-256；各 txt 是本地原始退出输出。
Windows / Python 3.12.10：76 passed、1 skipped；pip check 和四个离线场景退出 0。
跳过项是需要 Windows 开发者模式或权限的真实符号链接测试，不代表已验证。
既有真实跨文件记录位于 docs/live-smoke-example.json；它不是完整真实评测。
旧 MVP 6.3 对应新 9.1，旧 6.4 对应新 9.2，均需单独实测和审核。

Java 可选依赖：tree-sitter 0.25.2、tree-sitter-java 0.23.5。
本机 Windows Python 3.12 安装和最小解析已验证。Linux 本地未运行；后续 CI
覆盖 Linux，但在收到 CI 结果之前不能宣称该平台通过。
仅 literal 使用者无需安装解析器；需要 indexed 时安装 `pip install '.[indexed]'`。
开发和验证环境使用完整 requirements-lock.txt。
