# 流程图约定

本目录用 Graphviz DOT 维护跨模块流程、依赖、责任归属和状态索引。DOT 是唯一图源；不同时维护 YAML、手绘图或提交生成的 SVG。

## 为什么选择 DOT

- `digraph`、`subgraph cluster` 和边足以表达串联、分支与模块边界。
- `class`、`URL` 和 `tooltip` 是紧凑的机器可读属性；渲染为 SVG 后仍可用于链接和 CSS 选择。
- Graphviz、VS Code Graphviz Preview、JetBrains 插件和多个在线查看器都能直接打开。
- 语法稳定且文本 diff 清晰，比 GraphML 简短，也不需要为 Mermaid 另造 tag sidecar。

## 最小模式

节点只使用以下信息：

```dot
stable_id [
  label="Human label\nvisible status"
  class="backend status-working evidence-natural"
  URL="../modules/backend.md"
  tooltip="Short boundary description"
];
```

- ID 使用稳定的 `snake_case`，重命名显示文字时不要顺带改 ID。
- `class` 是空格分隔的 tag。优先使用 `backend`、`game-server`、`client`、`runtime`、`reference`，以及 `status-working`、`status-partial`、`status-missing`、`status-goal`。
- 只有证据边界明确时才增加 `evidence-natural`、`evidence-forced` 或 `evidence-synthetic`。
- `URL` 指向事实的权威 module 或 research 文档；图内不复制详细协议、地址和实验结论。
- 实线表示目标运行顺序，虚线表示实现依赖，点线表示只用于验证的参考路径。

状态描述的是节点标签所指的有限职责，不代表整个模块已经完成。例如 `gamestate` 的 `status-partial` 只表示 parser-compatible 骨架存在。

## 维护纪律

1. 跨模块顺序、责任或状态变化时，在同一提交更新图和对应权威文档。
2. 总图保持约 30 个节点以内。细节超过该规模时新增模块级 `.dot`，总图只保留一个入口节点和链接。
3. 不为每个函数建节点；只有影响状态所有权、协议阶段或诊断边界的步骤才进入图。
4. 不在图中维护长篇说明、日期流水账、offset 表或待办列表。
5. 新会话先用 tag 定位相关节点，再读取其 `URL` 指向的文档和代码。

快速筛选：

```powershell
rg 'status-missing|game-server' .agents\pipelines
```

安装 Graphviz 后可在本目录生成临时 SVG：

```powershell
dot -Tsvg codol.dot -o codol.svg
```

`codol.svg` 是本地预览产物，不提交。
