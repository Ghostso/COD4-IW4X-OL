# TRANSPORT_NOTE

本任务没有重新定义目标 netchan。

已核实：

- EXE 运行时镜像包含 OOB 与应用状态相关代码。
- 主 DLL 才是引擎模块，包含 `.text` 与 `.tvm0`。
- 现有服务器的 legacy 13B 和 2697 netchan 都是 `SERVER_ONLY`，没有目标模块证据。

未核实：

- 目标 netchan 的头部、序列号、分片、重组、可靠性与缓冲传递方式。

因此本任务只记录“缓冲区→解析入口”未闭合，不建立新的传输格式。
