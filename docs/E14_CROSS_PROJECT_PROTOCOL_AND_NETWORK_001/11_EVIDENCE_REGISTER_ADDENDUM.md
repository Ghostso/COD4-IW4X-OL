# 11 — 证据登记（E-14 追加）

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 及 E-10..E-13 的同名追加。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-14-01 | REFUTE | `0x60E5B0` | **非协议状态机**，是 vsnprintf 风格格式化器：`0x60E625 cmp al,0x25`（`'%'`）+ `0x60E73E jmp [eax*4+0xA0EF84]`（7 项转换符表） | `_data/out_60e5b0_head.txt`、`_data/out_fmt_vtable.txt` | PROVEN |
| EV-14-02 | CALLBACK | `0x60E470` | putc 回调：`mov [edx],cl` + `inc [eax]` + `cmp ecx,[eax+8]`（容量检查） | `_data/out_60e5b0_head.txt` | PROVEN |
| EV-14-03 | CALLPATH | `0x6029A0`→`0x602760`→`0x60E5B0` | recv **错误日志**路径：`push 0xC37244`（`"Recv failure: %s"`）→ `0x60E5B0` 格式化；`mov [ecx+0x85F4],edx` 记错误码 | `_data/out_paths.txt` | PROVEN |
| EV-14-04 | CRYPTO | 客户端镜像 | 内联 **OpenSSL 0.9.8p 16 Nov 2010**：字符串 `0xC3D0D2` 等 5 处 + `"SSL routines"` `0xC9F428` | `_data/out_t08_sslver` | PROVEN |
| EV-14-05 | SSLOBJ | `0x672460` | OpenSSL 对象方法分派：`cmp [eax+0x20],0` → 错误报告（`push 0xC5650C`）→ `mov ecx,[eax+8]` → `mov eax,[ecx+0x1c]` → `jmp eax` | `_data/out_paths.txt` | PROVEN |
| EV-14-06 | TLSPATH | `0x605220`→`0x5FB510`→`0x6104D0`→`0x672460` | TLS 读路径：`cmp [edi+0x5b8],0`（SSL 对象）+ `call 0x9FB510`（SSL_pending 类）+ `recv` 2 字节 peek | `_data/out_paths.txt` | PROVEN |
| EV-14-07 | VTABLE | `.rdata` `0x898580`–`0x898600` | `0x898588` 含 `0xb75a50`（recv）；`0x898590` 含 `0xb75ab0`（recvfrom） | `_data/out_paths.txt` | PROVEN |
| EV-14-08 | MERGE | `0x605220` vs `0x6029A0` | 6 层下游闭包大小 7 vs 39；**共享下游 = 0** | `_data/out_t09_merge` | REFUTED（汇合） |
| EV-14-09 | BITWIDTH | 服务端 `0xA085F` | A2 段计数 `mov dword [esp+8],0xB`（**11 bit**）→ 与客户端 `0xA2765 push 0xB` 一致 | `_data/out_t14_bits` | PROVEN（修订 E-08） |
| EV-14-10 | CONST | 客户端 `.text` | CODOL 分片常量 `0x489`/`0x70CC729` 命中 **0** | `_data/out_t08_sslver` | PROVEN（负） |
| EV-14-11 | REPO | 本地 git 副本 | IW4X `d1b175da1a25d31043246de103a702b206269e5a`；CoD4x `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | `git rev-parse HEAD` | PROVEN |
| EV-14-12 | REMOTE | GitHub API | `iw4x/iw4x-client` 默认分支 `main`（pushed 2026-10-07）；`callofduty4x/CoD4x_Server` 默认分支 `master`（pushed 2026-09-18） | `api.github.com` HTTP 200 | PROVEN |
| EV-14-13 | BFS | `0x350170` 上游 | 反向 4 层收敛为 9 函数；`0x34E7C0` = `cl_demo_jumptostart` 回调（E-12 已证） | `_data/out_bfs_up.txt`（E-12） | PROVEN |
| EV-14-14 | REFUTE | E-13 §候选 | E-13 登记的 4 条候选（`0x6029A0`/`0x605220`/`0x60E5B0`/`0x1B0430`+`0x78772D`）中 **3 条被排除** | 本表 EV-14-01..06 | REFUTED |
