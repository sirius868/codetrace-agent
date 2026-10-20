# 固定仓库基准 v2

本目录只保存原创问题/事实标注、源码路径/行号/哈希，不分发三个项目源码。
标注由助手实际阅读以下固定提交后编写，annotation_source=assistant_draft，仍需人工审核。
真实答案的human审核与标注来源分别记录，不把助手草稿作为human评分。

| repo_id | 来源与固定提交 | 分组 | 可读Java/Python文件 | 许可证正文 |
|---|---|---|---:|---|
| spring-petclinic | [500158f](https://github.com/spring-projects/spring-petclinic/tree/500158f732419217507c7656904b8e6aa1bcc0d6) | development | 50 | [Apache-2.0](https://github.com/spring-projects/spring-petclinic/blob/500158f732419217507c7656904b8e6aa1bcc0d6/LICENSE.txt) |
| flask | [d086db8](https://github.com/pallets/flask/tree/d086db856be187255b8ec61ef409357393020f32) | development | 83 | [BSD-3-Clause](https://github.com/pallets/flask/blob/d086db856be187255b8ec61ef409357393020f32/LICENSE.txt) |
| mall-tiny | [a81ec47](https://github.com/macrozheng/mall-tiny/tree/a81ec4740a0c7c99a06ebffb43a14168beadffc3) | held-out | 80 | [Apache-2.0](https://github.com/macrozheng/mall-tiny/blob/a81ec4740a0c7c99a06ebffb43a14168beadffc3/LICENSE) |

2026-10-20 本地核对提交、许可证正文和安全可读清单：105、139、98个文件。
Petclinic的`src/main/resources/static/resources/css/petclinic.css`超过256000字节，
不在可读源码清单内；索引报告partial。未增大预算、删源码或变更固定提交。
扫描截断/累计预算/访问失败会拒绝基准；超大、二进制和非UTF8文件按原工具边界不收录。

外部源码由用户在项目根目录外准备，不执行构建、不下载目标依赖。示例：

```powershell
git -c core.autocrlf=false clone https://github.com/spring-projects/spring-petclinic.git ../codetrace-benchmarks/spring-petclinic
git -C ../codetrace-benchmarks/spring-petclinic -c core.autocrlf=false checkout --detach 500158f732419217507c7656904b8e6aa1bcc0d6
git -c core.autocrlf=false clone https://github.com/pallets/flask.git ../codetrace-benchmarks/flask
git -C ../codetrace-benchmarks/flask -c core.autocrlf=false checkout --detach d086db856be187255b8ec61ef409357393020f32
git -c core.autocrlf=false clone https://github.com/macrozheng/mall-tiny.git ../codetrace-benchmarks/mall-tiny
git -C ../codetrace-benchmarks/mall-tiny -c core.autocrlf=false checkout --detach a81ec4740a0c7c99a06ebffb43a14168beadffc3
```

保持LF原始文件以匹配SHA-256。repo-map.example.json将公共repo_id映射到本地目录，
运行器检查Git根、origin、完整提交、清单及逐文件内容；源码变脏、漏项、别名目录均拒绝。
许可证文件也单独校验。两模式针对同一固定源码。不要在基准目录放运行产物。

每仓库8题（入口1/跨文件2/配置1/异常2/无答案2）；共24题、48个模式组合。
每个证据组允许多个等价范围；组内任一有效引用覆盖即可，跨组必须分别满足。
不把参考检索词、预期事实、片段或审核结果提供给真实模型。

mall-tiny在开发运行完成并冻结程序/提示/检索规则后才能真实运行。标注时读源码不等于
运行调参；若后续根据保留集结果修改实现，须披露已用于开发并重新选择保留集。
公开代码可能已在模型预训练中出现，本协议不证明模型从未见过代码。

Apache分发需保留许可证及适用通知；BSD需保留版权、条件、免责声明，不能借维护者背书。
本目录的哈希与原创描述不复制源码。模型执行记录可能包含源码摘录，默认保存在忽略的runs；
公开含摘录报告前应一并保留对应上游许可证/版权通知。不要将上游许可证删除或改称本人原创。
