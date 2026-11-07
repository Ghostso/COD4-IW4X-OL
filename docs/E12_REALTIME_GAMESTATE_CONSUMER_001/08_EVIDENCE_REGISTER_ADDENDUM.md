# 08 — 证据登记（E-12 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 及 E-10/E-11 的同名追加文件。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-12-01 | IMPORT | PE 导入表 | 网络锚点：`recv` IAT `0xBAE490`、`recvfrom` `0xBAE50C`、`send` `0xBAE4C8`、`sendto` `0xBAE504`、`select` `0xBAE4D8`；文件锚点 `ReadFile` `0xBAE22C`、`CreateFileA` `0xBAE1E4` | `_tools/t21_imports.py` | PROVEN |
| EV-12-02 | CALLSITE | 收包调用点 | `recvfrom`×3（`0x1B0BA1`/`0x6B4E3C`/`0x775ADE`）；`recv`×6（`0x602441`/`0x6029BE`/`0x6052AB`/`0x775A6C`/`0x784F7D`/`0x788133`） | `_data/out_iat_callers.txt` | PROVEN |
| EV-12-03 | STRUCT | `[0x743DE9C]+0x8048` | 3 MB 应用层环形缓冲；`+0x30AF2C`=写游标、`+0x30AF30`=读游标 | `_data/out_t12_buffer2` | PROVEN |
| EV-12-04 | PRIMITIVE | `0x3524F0` | **写侧**：`memcpy(ring+write, src, len)` @`0x352559`，容量 `0x300000` | `_data/out_t14_3524f0` | PROVEN |
| EV-12-05 | PRIMITIVE | `0x352570` | **读侧**：`memcpy(dst, ring+read, len)` @`0x3525D9`，返回 `len` | `_data/out_t14_3524f0` | PROVEN |
| EV-12-06 | POINTER | `[client+0x89244]` | 读取器指针仅 3 处写入：`0x35141E`→`0x752570`；`0x3515D9`/`0x356701`→`0x74F090` | `_data/out_t27_verify.txt` | PROVEN |
| EV-12-07 | CMDREG | `0x34E1B0` | `mov [0xDD4BF44],0x74E7C0` + `call 0x59DCA0`；命令名 `0xCD61D8`=`cl_demo_jumptostart` | `_data/out_34df80_reg.txt`、`_data/out_t37_names.txt` | PROVEN |
| EV-12-08 | STRING | `0xCD61B4`/`0xCD61C4`/`0xCD61D8`/`0xCD61EC` | `cl_demo_play`/`cl_demo_timedemo`/`cl_demo_jumptostart`/`cl_demo_keyboard` | `_data/out_t37_names.txt` | PROVEN |
| EV-12-09 | STATE | `0x8F1D0` | `cmp [0x1BBBCFC],7` / `jl` 返回；`cmp eax,7` / `cmp eax,9` / `jge`；仅状态∈[7,9) 调 `0x350170` | `_data/out_gsupdate_callers.txt` | PROVEN |
| EV-12-10 | STATEVAR | `0x1BBBCFC` | demo/回放状态机（0–10），全镜像 166 处引用 | `_data/out_state_var.txt` | PROVEN |
| EV-12-11 | STRING | `0xCD6384` | `EXE_ERR_PROCESS_DEMO_FILE_FAILED`（辅助证据，非单独依据） | `_data/out_t10_batch2` | PROVEN |
| EV-12-12 | CONFLICT | `0x34FD80(1)` vs `0xA21B8` | 客户端字段序 `{i32,i32,u32 len,payload}`；服务端 `{i32,cstr,cstr,i32,<cfgsub>,i32,i32,0x06}` → 第 2 字段即冲突 | `_data/out_34FD80.txt`、`_data/out_server_gamestate.txt` | REFUTED（匹配） |
| EV-12-13 | NULL | 收包函数 8 层下游 | 未到达 `0x350170`/`0x3547D0`/`0x354100`/`0xA2660`/`0x34FD80` | `_tools/t23_recvchain.py` | 未发现（不升级） |
| EV-12-14 | NULL | `0xA2E50` | 直接调用者 0；数据指针引用 0 | `_data/out_t10_batch2` | 未发现（不升级） |
| EV-12-15 | BITWIDTH | 客户端 `0xA2765` | A2 段计数读取 `push 0xB`（11 bit）；服务端历史记录为 10 bit | `_data/out_t32_pushes.txt` | BLOCKED（服务端未复核） |
| EV-12-16 | BFS | `0x350170` 反向 4 层 | 上游收敛为 9 个函数（depth1: `0x8F1D0`,`0x3512A0`；depth2: `0x9CFE0`,`0x34E7C0`,`0x3519F0`,`0x351A10`,`0x356580`；depth3/4: `0x1A9060`,`0x1A9760`） | `_data/out_bfs_up.txt` | PROVEN |
