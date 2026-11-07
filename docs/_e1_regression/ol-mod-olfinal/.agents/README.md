# 文档归属

- `AGENTS.md`：唯一必读入口；维护长期协作原则、上下文恢复协议和最新 handoff。
- `modules/backend.md`：DW3 控制面、存储、房间、matchmaking 和 booking 的权威模块说明。
- `modules/game_server.md`：连接、传输、gamestate 和 authoritative world 的权威模块说明。
- `modules/game_server_coverage.md`：玩家实体、多客户端调度和 SD 状态机的当前全链路覆盖表。
- `modules/runtime.md`：启动、自动化、Frida 和捕获操作规范。
- `modules/reverse_engineering.md`：IDA 主库、地址、annotations 和参考库纪律。
- `pipelines/*.dot`：跨模块顺序、责任和状态的可筛选图索引；详细事实仍归属 module/research。
- `research/*.md`：历史证据、反编译记录和实验快照，不承担当前进度或路线图职责。
- `../docs/devlog/*.md`：经过取舍的中文开发历程和心得，不承担当前实现状态职责。
- `../docs/references/`：保留来源与作者归属的外部文章、翻译和参考材料。

## 维护规则

- 一个事实只设一个权威位置；其他文件用链接或一句摘要引用。
- 根 `README.md` 只面向构建和使用，分发细节只在 `distribution/README.md`。
- 研究文档保留当时语境，顶部必须说明状态；其中的 `current`、覆盖率和建议默认只对记录时点有效。
- 当前状态变化时更新 `AGENTS.md` handoff；稳定边界变化时更新对应 module；不要在 research 尾部追加流水账。
- 跨模块顺序或责任变化时同步更新 `pipelines/codol.dot`；不提交生成的 SVG。
- 过时内容直接删除、改写或标记 superseded，不通过新增一份近似文档规避整理。
- 中文 UTF-8 是默认语言，技术标识保持英文；不为语言统一改写无证据结论。
- 开发历程只在重要结论和里程碑形成时整理；平时使用单一轻量素材入口，不让叙事写作拖慢核心开发。
- 外部全文、翻译和媒体必须记录来源基准与资源策略；参考项目内容不能升级为 CODOL 权威事实。
