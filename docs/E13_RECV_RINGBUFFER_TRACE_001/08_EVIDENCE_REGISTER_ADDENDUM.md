# 08 — 证据登记（E-13 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 及 E-10/E-11/E-12 的同名追加文件。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-13-01 | IO | 9 个收包函数 | 接收缓冲与容量均由调用者栈参数提供（`[ebp+8]`/`[ebp+0xc]`），函数本身不做缓冲 | `_data/out_recv_bodies.txt` | PROVEN |
| EV-13-02 | VTABLE | `.rdata 0x898588`/`0x898590` | `0x775A50`(recv)/`0x775AB0`(recvfrom) 为虚表相邻槽位（`0xb75a50`/`0xb75ab0`） | `_data/out_t09_ptr.txt` | PROVEN |
| EV-13-03 | CALLGRAPH | 9 收包函数 × 3 层 | 并集 179 个函数；到 `0x3524F0` 的已证调用边 **0** | `_data/out_3level.txt` | PROVEN（负） |
| EV-13-04 | NULL | 179 函数闭包 | 对 `0x743DE9C`/`+0x30AF2C`/`+0x30AF30`/`+0x8048` 的引用 **0**（全 `.text` 共 196 处） | `_data/out_globals.txt` | PROVEN（负） |
| EV-13-05 | CALLERS | `0x3524F0` | 直接调用者 22 处，**全部**位于 `0x351D00`；数据指针 2 处亦在 `0x351D00` | `_data/out_writer_audit.txt` | PROVEN |
| EV-13-06 | UNIQUE | `0x3524F0` | 无第二写入者；`+0x30AF2C` 其他写入仅 `0x356580`（重置） | `_data/out_writer_audit.txt` | PROVEN |
| EV-13-07 | CHAIN | `0x350170`→`0x34FD80`→`0x351D00`→`0x3524F0` | 每一跳均为唯一调用者 | `_data/out_t05_callers.txt` | PROVEN |
| EV-13-08 | DIRECTION | `0x351D00` | 序列化本地状态 → 写环形缓冲 → `0x753A40`/`0x756760` 提交（**发送**方向） | `_data/out_351d00.txt` | PROVEN |
| EV-13-09 | SEMANTICS | `0x352570` | 可读长度由调用者 `len` 决定；不读写游标、不算可读字节、无队列语义 | `_data/out_readerptr.txt` | PROVEN |
| EV-13-10 | CURSOR | `+0x30AF2C`/`+0x30AF30` | 写侧不读读游标，读侧不读写游标（互不感知） | `_data/out_writer_audit.txt`、`_data/out_readerptr.txt` | PROVEN |
| EV-13-11 | POINTER | `[+0x89244]` | 3 处写入值 = `0x752570`（W1）、`0x74F090`（W2/W3）；**均非解析器** | `_data/out_readerptr.txt` | PROVEN |
| EV-13-12 | INDIRECT | 收包闭包 | 未闭合间接调用：`0x60E5B0` `call [ebp-0xd2c]`×20+、`call ebx`×4；`0x60264A jmp [edx*4+0xA026D0]`；`0x787982 call 0xDBEF28A`（`.tvm0`） | `_data/out_globals.txt` | BLOCKED |
| EV-13-13 | REFUTE | 收包 → `0x3524F0` | 限定范围内 REFUTED（3 层闭包无任何边） | `_data/out_3level.txt`、`_data/out_globals.txt` | REFUTED（限定） |
| EV-13-14 | REFUTE | `0x3524F0` 为接收缓冲 | 实为发送序列化暂存（唯一调用链属 demo） | `_data/out_351d00.txt` | REFUTED |
| EV-13-15 | REFUTE | `[+0x89244]` → 解析器 | 3 处写入值均非 `0x350170`/`0x3547D0`/`0xA2660` | `_data/out_readerptr.txt` | REFUTED |
