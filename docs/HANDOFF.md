# 当前项目状态

更新日期：2026-10-20。

- 用户已选择重新创建 LangGraph 项目；这不是旧项目循环的迁移版本。
- 当前项目：`D:\_Workspace_\ai_agent\codetrace-agent`。旧项目由用户移至 `D:\_Workspace_\ai_agent\backup`，本次未修改旧项目。
- 独立 Python 3.12.10 虚拟环境，核心执行引擎 LangGraph 1.2.16。
- 已实现四个只读工具（概览、列表、搜索、按行读取），model/tools/validate/repair 四节点 StateGraph、严格结构契约及任务内证据快照、一次修正、模型/工具/上下文/总时限预算、重复调用拦截、四个离线场景和原子 JSON 记录。
- 已实现 Python/Java 共10题版本化标注、默认离线评测、显式真实模式、逐题报告与人工评分导入，并提供12个面试问题及源码指引。
- 已验证：独立 Python 3.12 环境按快照安装，75 项测试通过、1 项符号链接测试因 Windows 权限跳过，pip check、四场景及10题离线评测通过。详见 VERIFICATION.md。
- 已在被 Git 忽略的本地 .env 配置 DashScope 和 qwen3.8-27b，一次真实跨文件 smoke test 已完成；密钥不进入版本库。完整真实评测和人工审核仍待完成。
- 没有复制旧项目应用代码，也没有添加 LICENSE 文件；保留用户对旧项目 LICENSE 删除状态的选择。
- Git main 分支此前已推送至 https://github.com/sirius868/codetrace-agent ，关联 origin/main。Windows/Linux 离线 CI 已配置，远程执行结果未核实。
- OpenSpec deliver-codetrace-analysis-mvp：26/28项完成，6.3只完成一个跨文件用例，6.4尚未执行，未归档。用户原有未跟踪的 .agents 与其他 OpenSpec 配置/归档未纳入实现提交。
- 后续优先阅读 `src/codetrace/graph.py` 并学习节点与状态，再完成剩余真实 smoke 和人工评测。不要声称已实现向量检索、任务恢复、Web 服务或完整真实模型成功率。

运行命令和限制见项目 README。工作区 `docs` 中的旧方案已加历史说明。
