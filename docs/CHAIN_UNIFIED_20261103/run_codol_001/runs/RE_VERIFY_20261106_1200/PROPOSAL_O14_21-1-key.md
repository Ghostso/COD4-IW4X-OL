# 提案 O14 —— 大厅 `21/1` 必须取走客户端的 16 字节密钥

> **状态：仅提案，未实施。**
> `REF_LOBBY_KIT\lobby_server.py` 属于 `AGENTS.md` 列出的**受保护资产**，
> 除非用户明确要求基线迁移，否则不得编辑/覆盖。
> 本文件放在 run 目录里，不改动 kit。

## 1. 证据链（全部来自 3.19 本地逆向，地址+字节）

```
A-phase 0x7F4630(S, container)                      ; S = dwRoom+0x20
  0x7F46A3  lea ecx, [esi + 0x1cc]                  ; 目标缓冲 = S+0x1CC（16 字节）
  0x7F46A9  push 0x10
  0x7F46B3  call 0xB771A0
    0xB771AB  call 0xBB1220
      0xBB124B  mov  eax, [0xE85C90]
      0xBB1253  call dword ptr [0xCA8008]           ; ★ 现场“取”出 16 字节（装载期解析的外部函数）
  0x7F46CC  call 0xB9AE30                           ; 21/1 组包
    0xB9AE7F  call 0xBA72C0  (svc=0x15, task=1, …)  ; ★ 21/1
    0xB9AE9D  call 0xBA74B0                         ; 把 S+8 序列化进请求体
      0x806D8F  push 0x10                           ; ★ 16
      0x806D91  lea edx, [esi + 0x1c4]              ; ★ S+8+0x1C4 = S+0x1CC
      0x806D9A  call 0xB767D0                       ; ★ 写成 DML blob
  完成回调 0x7F45A0(ok≠0)：
    0x7F460B  call 0x7F5A50(&S+0x10, &S+0x1CC)      ; ★ 同一个值插入 N+0x40
      0x7F5A50 → 0x643300 → 0xBAC600 → 0xBB1A90 → 0xBB9D40(key, value)
```

**结论**：

- `N+0x40` 的 16 字节值 = `S+0x1CC` = **客户端在 A-phase 现场取出/生成的那一份**。
- 同一份值被**同时**写进 `21/1` 请求体上行给大厅。
- `scanrw` 扫 `0x1CC` 的全部写点，`0x62xxxx/0x63xxxx` 区只有 mmrsv 那一处
  （且是另一个对象 `dwRoom+0x38528`）⇒ `S+0x1CC` **没有第二个写者**，不会被网络回包覆盖。
- `N+0x40` 的**查表键**（8 字节）来自 `21/1` **应答**：`0xB94AF0` 把它读到 container+0x10，
  `0x7F45A0` 取 `[[reqObj+0x1C]+0x10]` → `S+0x10`。（这与大厅现回的 `SESSION_ID` 一致，OK。）

**⇒ 现状缺陷**：`lobby_server.py:1230-1237` 的 `21/1` 分支
只 `return [ob.blob(struct.pack("<Q", SESSION_ID))]`，**完全不解读来访的 16 字节**；
而战斗服 `src/battle/battle.c` 的 `load_security_key()` 读的是
`battle_security_key.txt`（由 `SEC_KEY = _load_sec_key()` 写出，现为 32 个 ASCII `'0'`
⇒ 16 个零字节）。**两边用的不是同一份密钥。**

## 2. 线上定位方式

`21/1` 请求体是 `S+8` 的 DML 序列化。**`0xBA74B0` 调的正是 `S+8` 的 `vt[0]`**
（`0xBA74E5 mov eax,[edx]`；`[0xDC79FC] = 0x806C90`），字段顺序（`0x806C90` 逐条读出）：

| # | 写入点 | 字段 | 真机抓包对照（`ONCE_20261106_001100` `#57`） |
|---|---|---|---|
| 1a | `0x806C9B` `0xB95B30` → `0xB95B47` | `blob(this+0x10, len=[this+0x110])` | `13 08 43 00 00 00` + 67B ✅ |
| 1b | `0xB95B59` `0xB766B0` | `u32 [this+0x114]` | `08 00 00 00 00` ✅ |
| 1c | `0xB95B6B` `0xB766B0` | `u32 [this+0x118]` | `08 0c 00 00 00` ✅ |
| 2 | `0x806CB3` `0xB76700(+0x120, 0x40)` | 0x40 字节缓冲（玩家名） | `10 "M7-E8S6Client"` ✅ |
| 3 | `0x806CD0` `0xB76120(+0x160, +0x164)` | 指针+长度 | （日志 hex 已在 256 字符处截断） |
| 4 | `0x806CE8` `0xB76700(+0x168, 0x40)` | 0x40 字节缓冲 | — |
| 5–11 | `0x806CFE … 0x806D82` | `+0x1a8/1ac/1b0/1b4/1b8/1bc/1c0` 标量 | — |
| **12** | **`0x806D9A` `0xB767D0(+0x1c4, 0x10)`** | **★ 16 字节 blob（就是它）** | — |
| 13… | `0x806DB0 …` | `+0x1d4/1d8/1dc/1e0/1e4/1e8/1ec` 标量 | — |

**前 4 个字段已被真机 payload 逐字节验证**（`payload(269)`，`declared=272`），
这是本条提案最重要的可信度依据 —— 字段序不是我推的，是抓包对上的。

DML blob 的线上编码 = `13 08 <u32 len LE> <原始字节>`，
所以这 16 字节就是 **`13 08 10 00 00 00` + 16 字节**。

## 3. 建议改动（**未实施**，待批准）

位置：`REF_LOBBY_KIT\lobby_server.py:1230-1237`

```python
if service in (0x15, 0x8A) and task == 1:
    ob = cc.Buf()
    ob.blob(struct.pack("<Q", SESSION_ID & 0xFFFFFFFFFFFFFFFF))
    # ★ 新增：把客户端上行的 16 字节密钥取出来，交给战斗服
    _k = _extract_client_sec_key(plain)
    if _k is not None:
        try:
            with open(SEC_KEY_FILE, "w", encoding="ascii") as f:
                f.write(_k.hex())
            log("   ★ 21/1 客户端 16B 密钥 = %s（已写给战斗服）" % _k.hex())
        except Exception as e:
            log("   写 battle_security_key.txt 失败: %r" % (e,))
    return [ob.data()], (...), []
```

建议的提取函数（保守：只认 `13 08 10 00 00 00` + 16 字节，且要求不是全零）：

```python
def _extract_client_sec_key(plain):
    """从 21/1 请求体里取序列化体第 12 字段的 16 字节。
    依据：0x806D8F push 0x10 / 0x806D91 lea edx,[esi+0x1c4] / 0x806D9A call 0xB767D0
    （S+8 序列化体，字段 12；DML blob 编码 13 08 <u32> <data>）。"""
    b = plain or b""
    needle = b"\x13\x08\x10\x00\x00\x00"
    i = b.find(needle)
    if i < 0:
        return None
    key = b[i + 6:i + 6 + 16]
    if len(key) != 16 or key == b"\x00" * 16:
        return None
    return key
```

⚠ 之所以要 `!= 全零` 的保守判断：`0xBB1220` 的失败分支不会写缓冲，
若那里失败，缓冲可能保持原值或全零，全零没有意义。

## 4. 验证方案（新 run 目录，未执行）

1. 新建 `run_codol_001\runs\<RUN_ID>\`，按 `run_frozen_chain_once.py` 复制 kit 后**只在该副本里**改。
2. 打开 `21/1` 与 `battle_security_key.txt` 的日志。
3. 成功判据：`21/1` 打印出的 16B **非全零**，且与 `battle_security_key.txt` 内容一致，
   战斗服启动日志 `[battle] securityKey <- battle_security_key.txt (XX…)` 与之逐字节相同。
4. 仍需用户明确批准（受保护资产 + 「不再实机」的现行指令）。

## 5. 残留不确定性（已书面穷尽静态手段）

- `[0xCA8008]` 的值 `0x116F2D01` **不在镜像任何段内**（镜像 0x401000–0xEA59000），
  且它位于第 2 段开头 `0xCA8000` 起的一张同类指针表里 ⇒ **装载期填充**，文件镜像读不出被调者。
- `[0xE85C90]` = `0x0EB82920`，同样越界。
  ⇒ 无法静态判定该函数是"随机生成"还是"别处取来"；但**无论哪种，
  值都在客户端侧产生并上行**，所以"大厅需要转发"这个结论不受影响。
