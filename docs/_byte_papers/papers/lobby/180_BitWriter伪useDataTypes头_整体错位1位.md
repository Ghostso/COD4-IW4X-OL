# 180 · 房间类第三个致命 bug：`BitWriter` 伪造了 1 位 `m_useDataTypes` 头

> 卷次：180（房间类 · 线格式实测）
> 方法：把 `Manifold::serialize` / `deserialize` 的**第一条指令**看清
> 结论：**不存在 1 位 `m_useDataTypes` 头。服务端全部 dwRoomMessage 位流整体偏移了 1 位。**

---

## §0 结论

`lobby_server.py` 的 `BitWriter.__init__` 无条件执行：

```python
if use_data_types:
    self.write_bits(1, 1)     # ← ★ 这 1 位是伪造的
```

**客户端从来没有这个 1 位头。**

⇒ 服务端产出的 `dwRoomMessageStartGame`（109 字节）**整体错位 1 位**，
   所有基于它的推送（mmstart / 11/4 trigger）全都对不上。

---

## §1 双向证据（写侧 + 读侧，第一条指令）

### 1.1 写侧 `0x625520 Manifold::serialize`

```asm
0x625520  push ebp / mov ebp,esp / and esp,0xfffffff8 / sub esp,0x24
0x625529  push ebx / push esi
0x62552B  mov esi,[ebp+8]
0x62552E  mov ebx,[esi]
0x625530  push edi
0x625531  mov edi,ecx
0x625533  mov al,[edi+4]          ; type
0x625536  push 3                  ; ★★★ 第一条业务指令
0x625538  mov ecx,ebx
0x625542  call 0xB77B10           ; W_TAG(3)
```

### 1.2 读侧 `0x6256C0 Manifold::deserialize`

```asm
0x6256C0  push ebp / mov ebp,esp / and esp,0xfffffff8 / sub esp,0x83c
0x6256DA  push ebx / push esi / push edi
0x6256DD  mov edi,[ebp+8]
0x6256E0  mov esi,[edi]
0x6256E2  mov ebx,ecx
0x6256E4  push 3                  ; ★★★ 第一条业务指令
0x6256E6  mov ecx,esi
0x6256F0  call 0xB774E0           ; R_TAG(3)
```

★★ **两侧第一条都是 `W_TAG(3)` / `R_TAG(3)`。中间没有任何 `write(1)` / `read(1)`。**

### 1.3 `0xB77A70` 的"包装头"分支确实存在，但没被启用

`0xB77A70` 里有一段：

```asm
0xB77A73  cmp byte ptr [ebp+0x14], 0     ; ★ 第 4 参
0xB77A82  je  0xB77AC3                    ; == 0 → 跳过整段
0xB77A84  push 0xC  / call 0xB77B10       ; W_TAG(12)
0xB77A91  push 8    / call 0xB77B10       ; W_TAG(8)
0xB77A9A  push 0x20 / call 0xB777C0       ; W_VAL(32, start)
0xB77AAA  push 8    / call 0xB77B10       ; W_TAG(8)
0xB77AB3  push 0x20 / call 0xB777C0       ; W_VAL(32, end)
```

★★ **如果第 4 参非 0，会写一个 5 段包装头。**

但 `0xB77B10` 调用时：

```asm
0xB77B19  mov eax, [ebp+8]    ; n
0xB77B1C  push 0              ; ← 第 4 个 push → 对应 [ebp+0x14]
0xB77B1E  push 0x1F
0xB77B20  push 0
0xB77B22  push eax
0xB77B23  call 0xB77A70       ; (this, n, 0, 0x1F, 0)
```

⇒ `[ebp+0x14] = 0` ⇒ **`je` 直接跳过包装头** ⇒ **不写。**

★ 这解释了为什么原作者会以为有 `m_useDataTypes` 头：他看到了这段包装头代码，但没注意第 4 参传的是 0。

---

## §2 影响范围

| 函数 | 影响 |
|---|---|
| `build_startgame_payload` (109 B) | **整体错位 1 位** |
| `BitWriter.write_blob` | 每个 blob 都错位 |
| `build_room_info` 等所有用 `BitWriter` 的 | 全部错位 |
| `build_manifold`（codol_crypto） | 无影响（未用 BitWriter） |

### 2.1 109 字节是怎么来的（修正后自洽）

```
W_TAG(3)                  5 位
W_VAL(3, 8)               8 位
blob(67B addr):  5+5+32 + 536 = 578 位
blob(8B sess):   5+5+32 +  64 = 106 位
blob(16B key):   5+5+32 + 128 = 170 位
                            ─────
                            867 位 = ceil(867/8) = 109 字节 ✓
```

★ 加 1 位伪头后是 868 位 = **109 字节（巧合相同）**。
**这也是为什么之前没人发现** —— 字节数没变，只是内部错位。

---

## §3 R19 已落地

```python
def __init__(self, use_data_types=False):
    """★ R19：不再写伪 m_useDataTypes 头。
       写侧 0x625520 / 读侧 0x6256C0 的第一条指令都是 push 3，
       流从第 0 位起就是 W_TAG(3)，没有 1 位前缀。"""
    self.buf = bytearray()
    self.bit_len = 0
    self.use_data_types = use_data_types
    # 不写任何头
```

**验证 `verify9.py` ALL PASS：**

| 断言 | 结果 |
|---|---|
| 构造后 `bit_len == 0` | ✅ |
| `write_tag` 后 5 位 | ✅ |
| `write_blob(2B)` = 5+5+32+16 = 58 位 | ✅ |
| `build_startgame_payload` = 109 字节 | ✅（867 位自洽） |

★ 回归 `verify3` / `verify4` / `verify8` / `import_test4` 全 PASS。

---

## §4 与前几卷的关系

| 卷 | 关系 |
|---|---|
| 169 | 「`WriteBits(8)` 零填充」→ 177 已推翻 |
| 175 | 「51 位头」→ 177 改为 50 位 |
| 176 | 「item tag 19 位」→ 177 改为 5 位标签 |
| 177 | 「5 位标签」→ **正确**，但位序说 MSB → 178 改为 LSB |
| 178 | 「LSB-first」→ **正确** |
| **180（本卷）** | **补上：不存在 1 位 `m_useDataTypes` 头** |

★ 四卷累计更正：位宽模型→5位标签、MSB→LSB、去掉伪头。
**每一次都是"只读函数开头几条指令"造成的。**

---

## §5 诚实边界

1. **仍然没有真实样本。** 33 run 的 6/5 应答全是空 TLV。
2. **109 字节这个数字是"巧合正确"** —— 加 1 位和不加 1 位都得 109 字节。所以之前没法用它发现错误。
3. **`build_room_push` 的信封层（`ob.u32(8)` + sender + room_id + blob）未经 5 位标签模型复核** —— 它是 TLV 而非位流，可能是另一套格式，本卷未动。
4. **`write_bits` 的默认 `nbits=5`** 与 `write_tag` 一致，但如果有调用方用 `write_bits(x)` 不带 nbits，会被默认成 5 位 —— 需要逐调用点核。

---

## §6 方法论

1. **★★★ 读函数要读到第一次"业务写入"，不是读到 `ret` 也不是读到前 5 条。** 本卷的关键就在 `0x625536 push 3` 这一条 —— 它是第一条业务指令。
2. **★★★ 两侧（写/读）第一条指令必须完全对称。** 都 `push 3` ⇒ 同一起点 ⇒ 无头。若一侧 `push 3`、另一侧 `push 1` 再 `push 3`，就说明有头。
3. **★★★ "字节数正确" 不能证明 "内部正确"。** 867 位和 868 位都是 109 字节。这是本次错误藏了这么久的原因。
4. **★★ 看到"看起来像头"的代码段，先查它的启用条件。** `0xB77A70` 那段包装头代码存在，但第 4 参恒 0。
