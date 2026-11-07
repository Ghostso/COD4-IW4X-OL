# 08 — 证据登记（E-11 追加）/ EVIDENCE REGISTER ADDENDUM

> 追加修订，不覆盖 `14_SERVER_KNOWLEDGE_ATLAS_001\_EVIDENCE_REGISTER.md` 与 E-10 的 `08_EVIDENCE_REGISTER_ADDENDUM.md`。

---

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-11-01 | DISPATCH | 客户端 `0x350170` | 顶层分派器：读 1 字节 opcode，`dec eax`，`cmp eax,3`，`jmp [eax*4+0x75025C]` | `_data/out_top_dispatch.txt` | DIRECT |
| EV-11-02 | TABLE | `0x75025C` | 4 项：1→`0x350040`，2→`0x34FD80(0)`，3→`0x34FD80(1)`，4→`0x3547D0` | `_data/out_top_dispatch.txt` | DIRECT |
| EV-11-03 | SUBFRAME | `0x354100` | 子帧分派器：`movzx [ebp+0xc]`，`cmp 8`，`jmp [eax*4+0x7547AC]` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-04 | LOOP | `0x3547D0` | 读 1 字节；`cmp al,9`/`cmp al,0xA` 退出；否则调 `0x354100` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-05 | CASE6 | `0x354697` | `memset 256KB` → `MSG_InitReadOnly` → 读 4 字节 LEN → 读 LEN 字节 → `0x352F80` | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-06 | CURSOR | `0x352FA1` | `inc eax; mov [esi+0x1C],eax`：进 body reader 前 +1 字节 | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-07 | READER | `[client+0x89244]` | 可插拔读函数指针：`0x35141E`→`0x752570`；`0x3515D9`/`0x356701`→`0x74F090` | `_data/out_3512a0_precise.txt` | DIRECT |
| EV-11-08 | SERVER | `0xA07F8` | `WriteByte(4)`，唯一调用者 `0xA22C1`（`WriteConfigstrings`） | `_data/out_srv_writer_and_prims.txt` | DIRECT |
| EV-11-09 | SERVER | `0xA0997`/`0xA22F8`/`0xA4CAF` | 三个 `WriteByte(6)`，层级不同 | `_data/out_srv_writebyte.txt` | DIRECT |
| EV-11-10 | SERVER | `0x99551` | `mov ecx,1` → `0x994FC` → `MSG_WriteData(len=1)` | `_data/out_srv_writer_and_prims.txt` | DIRECT |
| EV-11-11 | CONFLICT | `0xA21B8` vs `0x34FD80` | 服务端 `0x03` 体为 `{i32,cstr,cstr,i32,...}`；客户端 `0x34FD80` 为 `{i32,i32,u32 len,payload}`，字段序不匹配 | `_data/out_34FD80.txt` | DIRECT |
| EV-11-12 | REFUTE | E-10 `01` | E-10 字符串探测误传 VA 给 `bytes_rva`；E-11 用 `VA-ImageBase` 修正 | `_data/out_t03_xrefs.txt` | DIRECT |
| EV-11-13 | CLIENT | `0xA2660` | 进入后 `lea edi,[eax+2]` + `push 2` + `MSG_ReadData`：首字段 2 字节 | `_data/out_case6_chain.txt` | DIRECT |
| EV-11-14 | NULL | `0x350000-0x360000`/`0xA0000-0xA3000` | `cmp/sub == 4` 无消息读取比较；`cmp/sub == 6` 无字节流比较 | `_data/out_cmp4.txt`、`_data/out_cmp_scan.txt` | DIRECT（否定） |
| EV-11-15 | STRUCT | `0x1AC670` | 客户端 `MSG_ReadBits` 用 `[msg+0x20]` 作 bitpos；服务端用 `[msg+0x10]` | `_data/out_srv_writer_and_prims.txt` | DIRECT |
