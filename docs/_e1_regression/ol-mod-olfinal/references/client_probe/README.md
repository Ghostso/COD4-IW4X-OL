# Client Protocol Probes

这里保存曾经帮助客户端进入地图、恢复 DTLS/netchan/gamestate/snapshot 格式的 Python/Frida 工具。

这些工具包含合成 server descriptor、gamestate 或 snapshot，只能作为：

- 客户端 parser 和 framing 的可执行规格；
- 新 server 输出的差分对照；
- 地址、字段和状态机的历史证据。

它们不能作为 authoritative game server，也不能重新并入生产链路解决黑屏、出生点或低帧率问题。运行时需要把 `tools/runtime` 加入 `PYTHONPATH`，以复用 `CodolGame` 与 `CodolFridaRuntime`。
