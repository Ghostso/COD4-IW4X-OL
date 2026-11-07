# 214 · ★★★★ 整链打通：`mmbook accepted` + MMI+0x168/0x16C → `[+0x3A048/4C]` 对端 ID

> 卷次：214（房间类 · **开局链路决定性闭合**）
> 结论：`0xDC69B0` = `"mmbook accepted"`；`[+0x3A048/4C]` 从 **`MMI+0x168/0x16C`** 拷来。

---

## §0 `0xDC69B0` = `"mmbook accepted"`

```
0xDC6990: " %s %d; roomChatChannelID %llu;"
0xDC69A0: "ChannelID %llu;"
0xDC69B0: ★ "mmbook accepted"
0xDC69C0: "mp_trainingground"
0xDC69D0: "d"
0xDC69E0: "out"
```

★★★ **这就是记忆条目里反复出现的 `mmbook` / `mmbook accepted`！**

⇒ `0x632680` 的门 6 = **`strcmp(参数, "mmbook accepted")`**

★ 也就是说：**`0x632680` 处理的是"收到 mmbook accepted 字符串"的场景。**

---

## §1 `[+0x3A048/4C]` 的来源

### 1.1 `0x62F6F0` 里的赋值

```asm
0x62F736  mov ecx, [edi + 0x168]
0x62F73C  mov [esi + 0x3A048], ecx     ; ★ 从 MMI 元素取
0x62F742  mov edx, [edi + 0x16C]
0x62F748  mov [esi + 0x3A04C], edx     ; ★ 从 MMI 元素取
0x62F74E  lea edx, [edi + 0x170]       ; 接着取字符串
```

★★★ **`edi` = 选中的 MMI 数组元素**（`0x62F90E lea edi,[eax+ebx+0x7470]`）。

⇒ **`[+0x3A048/4C]` = `MMI+0x168` / `MMI+0x16C` 的副本。**

### 1.2 `MMI+0x168/0x16C` 是 197 卷记录的高区字段

199 卷 ctor `0x806B50`：
```asm
0x806BA7  mov dword [esi+0x168], 0
0x806BAD  mov dword [esi+0x16C], 0
```

★ ctor 把它们清零。而 `0x806F20`（serialize）读 `+0x168`。

⇒ **`MMI+0x168/16C` = 一个 u64（网络字段）**，由网络收发填充。

★★ **这几乎肯定是"对端/房间的 u64 ID"。**

---

## §2 完整链路（闭合）

```
① 服务端发 mmbook accepted（6/14 的应答）
        ↓
② 客户端 0x632680 处理
   门1: [esi+0x278] != 0
   门2: clientState < 3
   门3: [esi+0xE360] >= 0
   门4: [ebp+8]  == MMI+0x168（对端 ID 低）
   门5: [ebp+0xC] == MMI+0x16C（对端 ID 高）
   门6: strcmp([ebp+0x14], "mmbook accepted")
        ↓
③ 全过 → 取 MMI 数组元素 → 构造 StartGame → 0x62ABF0 发送
```

★★★ **服务端要触发开局，必须：**
1. 发 `mmbook accepted`
2. 携带**匹配 `MMI+0x168/0x16C` 的 u64 ID**
3. 客户端 `clientState < 3`（还没进房间）

---

## §3 这对服务端修复的直接指导

`lobby_server.py` 的 `6/14 mmbook` 分支：

```python
if re.search(rb"mmbook[^\x00]{0,120}", body):
    accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
    pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
```

★★★ **必须检查 `FR_BOOKING_ACCEPTED` 是否包含 `"mmbook accepted"` 字符串 + 正确的 u64 ID。**

★ 如果 `FR_BOOKING_ACCEPTED` 是 ol-mod 的抓包常量，那它的 ID 与本 build 客户端记录的 `MMI+0x168/16C` 必然不匹配。

⇒ **门 4/5 永远不过 ⇒ StartGame 永远发不出去 ⇒ 房间开局失败。**

★★ **这极可能就是"房间动作失灵"的真正根因！**

---

## §4 本卷确定结论

| 项 | 状态 |
|---|---|
| `0xDC69B0` = `"mmbook accepted"` | ✅ |
| `0x632680` 门 6 = strcmp `"mmbook accepted"` | ✅ |
| `[+0x3A048/4C]` 来自 `MMI+0x168/0x16C` | ✅ |
| `MMI+0x168/16C` = 高区网络字段（u64） | ✅ 197/199 卷 |
| **开局 6 门全过才发 StartGame** | ✅ |
| `FR_BOOKING_ACCEPTED` 是否含正确 ID | ⬜ **待查（关键！）** |

---

## §5 下一步（最高优先级）

**查 `codol_crypto.py` 的 `FR_BOOKING_ACCEPTED` 常量内容** —— 若不含 `"mmbook accepted"` + 正确 u64，就是根因。

---

## §6 方法论

1. **★★★★ 字符串常量的内容能直接定位业务语义。** `0xDC69B0` = `"mmbook accepted"` 一句话就把 `0x632680` 的用途定死了。
2. **★★★ `strcmp(参数, 常量)` 中的常量是"期望值"，是业务协议的一部分。**
3. **★★ 字段拷贝（`mov [A+0x168] → [B+0x3A048]`）能揭示"谁是谁的副本"。**
4. **★★★ 六道门全部列出后，"服务端要做什么"就变成机械推理。**
