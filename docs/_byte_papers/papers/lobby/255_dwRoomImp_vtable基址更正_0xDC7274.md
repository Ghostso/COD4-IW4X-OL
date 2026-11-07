# 255 · ★★★★ dwRoomImp vtable 基址更正 = `0xDC7274`（`0xDC73B0` 只是它的 `+0x13C` 槽）

> 卷次：255（房间类 · 坐标系更正）
> 方法：找 vtable 指针的**写点**（构造函数 `mov [obj], vt`），再核对 `[vt+0x13C]`
> 结论：dwRoomImp 单例在 `[0x82E13FC]`；其 **vtable 基址 = `0xDC7274`**（不是 191–216 卷用的 `0xDC73B0`）。
> `0xDC73B0 = 0xDC7274 + 0x13C`，即 `vt+0x13C = 0x632680`。

---

## §0 直接证据：构造函数写 vtable

```asm
; ---- dwRoomImp 构造函数 0x62C000 ----
0x62C000  push ebp / mov ebp,esp / push ecx / push ebx
0x62C005  mov ebx,[ebp+8]                 ; this
0x62C00C  mov [ebx+4..0x18],0             ; 低区清零
0x62C020  lea ecx,[ebx+0x20]
0x62C023  mov dword [ebx],0xDC7274        ; ★★★ 写 vtable 指针 = 0xDC7274
0x62C02C  call 0x806B50                   ; MMI 构造（[this+0x20] 是 MMI）
0x62C033  lea ecx,[ebx+0x258] / call 0xB94940
...
0x62C099  mov [ebp+0xc],0x31              ; 循环计数
0x62C0A4  call 0x806B50                   ; 建 50 个 MMI（[this+0x340] 起，步进 0x238）
0x62C0C2  call 0x806B50                   ; [this+0x7238] 单例 MMI
0x62C0D8  call 0x806B50                   ; 建 50 个 MMI（[this+0x7470] 起）
0x62C0E8  mov [ebx+0xE360],0xFFFFFFFF     ; MMI 数组索引 = -1
0x62C102  call 0x623770                   ; [this+0xE368] 起 19 个（步进 0x1D0）
0x62C280  mov [ebx+0x3A048],0           ; booking id 低
0x62C286  mov [ebx+0x3A04C],0           ; booking id 高
0x62C36F  ret 8
```

★ 该构造函数把 `0x3A048/4C`（booking id）、`0xE360`（MMI 索引）、`0x7470`（MMI 数组）都初始化了
⇒ **`0x62C000` 就是 dwRoomImp 的构造函数**，它直接把 vtable 写成 `0xDC7274`。

---

## §1 槽地址 vs 基址：`0xDC73B0 = 0xDC7274 + 0x13C`

`0x632680` 这个 dword 在全镜像只出现在两处：
```
0xDC73B0  ->  0xDC73B0 - 0x13C = 0xDC7274
0xDC7850  ->  0xDC7850 - 0x13C = 0xDC7714
```
⇒ 两个 vtable 基址 `0xDC7274`（主）/ `0xDC7714`（次），**`0x632680` 都在各自的 `+0x13C` 槽**。
`0xDC73B0` 与 `0xDC7850` 只是这两个基址的 `+0x13C` 槽地址。

**交叉验证**：`0x7F155C` 读 `[[0x82E13FC]]+0x13C` ⇒ 若对象 vtable = `0xDC7274`，则 `[0xDC7274+0x13C] = [0xDC73B0] = 0x632680` ✅。
若对象 vtable = `0xDC73B0`（191–216 的假设），则 `+0x13C` 会读到 `0xDC7434` —— 与"是 `0x632680`"矛盾。

---

## §2 dwRoomImp 单例在 `[0x82E13FC]`（分配 0x3A128）

```asm
; ---- 初始化函数 0x639D00 ----
0x639D03  push 0x3A128 / call 0xC3E9F5    ; ★ alloc(0x3A128)
0x639D19  call 0x62C000                    ; ★ dwRoomImp 构造
0x639D1E  mov [0x82E13FC],eax              ; ★★★ 单例指针
0x639D2B  push 0x3A160 / call 0xC3E9F5
0x639D3D  call 0x638210                    ; 派生对象构造（vtable 0xDC7714）
0x639D42  mov [0x82E1400],eax
0x639D4F  push 0x38 / call 0xC3E9F5
0x639D71  mov [esi],0xDC74E0               ; 第三个对象（0x38 字节）
0x639D88  mov [0x82E1404],esi
```

| 全局 | 对象 | 大小 | vtable 基址 | 构造 |
|---|---|---|---|---|
| `[0x82E13FC]` | **dwRoomImp** | `0x3A128` | **`0xDC7274`** | `0x62C000` |
| `[0x82E1400]` | 派生 room 对象 | `0x3A160` | `0xDC7714` | `0x638210` |
| `[0x82E1404]` | 小对象 | `0x38` | `0xDC74E0` | 内联 |

★★ `0x639D25`/`0x63A59A` 是 `[0x82E13FC]` 的两个写点（构造时 = `eax`；销毁时 = 0），与 `0x63A580..0x63A5A0` 的清理成对。

---

## §3 更正后的完整 vtable（基址 `0xDC7274`，关键槽）

| 槽 | 目标 | 身份 |
|---|---|---|
| `+0x000` | `0x6391E0` | slot0（虚析构族） |
| `+0x084` | `0x6301A0` | **SendReady**（154/228 卷的 `vt[33]`） |
| `+0x13C` | **`0x632680`** | **booking 应答处理**（227/254 卷） |
| `+0x140` | `0x62E9F0` | `mmrsv` 处理候选（244 卷） |
| `+0x144` | `0x62CA60` | `mminvite` 处理候选 |
| `+0x148` | `0x62C580` | **消息发送**（→`0x62C380`，254 卷） |
| `+0x14C` | `0x629730` | 底层发送（`0x6568F0`） |
| `+0x150` | `0x6297A0` | 发文本命令（booking 请求用它，244 卷） |

★★ **凡是旧卷写"`vt[33]` / `vt+0x84` / `vt+0x13C` / `vt+0x148`"的，基址都在 `0xDC7274`。**
旧卷把 `0xDC73B0` 当基址，是**把 `+0x13C` 槽地址当成了基址**（差 0x13C）。

---

## §4 附带新发现：dwRoomImp 内嵌一个新 MMI `[this+0x20]`

191–216 卷记录 MMI 在 `+0x7238` / `+0x7470`。本卷在构造函数里发现 **`[this+0x20]` 也构造了一个 MMI**（`0x62C02C call 0x806B50`）。
⇒ dwRoomImp 至少含 3 组 MMI：`+0x20`（单个）、`+0x340`(50)、`+0x7238`(1)、`+0x7470`(50)。
**P1（StartGame 用的 `MMI+0x18`）究竟落在哪一组，需按调用点用的 `[this+8]`/`lea` 决定**（198 卷判为低区缓冲，本卷不改写该结论）。

---

## §5 边界

| 项 | 状态 |
|---|---|
| dwRoomImp vtable 基址 = `0xDC7274` | ✅ 构造函数写点 |
| `0xDC73B0` = `+0x13C` 槽 | ✅ dword 位置计算 |
| 单例 = `[0x82E13FC]`，大小 `0x3A128` | ✅ |
| `+0x20` 也是 MMI | ✅（新） |
| 191–216 卷是否本就用 `0xDC7274` | ⬜ 其文本写"vt `0xDC73B0`"，本卷按字节证据取 `0xDC7274` |

---

## §6 方法论

1. **★★★★★ vtable 基址的唯一权威 = 构造函数里的 `mov [obj], imm32`。** 不要从"某槽地址"反推基址。
2. **★★★★ `0x6xxxxx` 数值散布时，先算相邻差：`0xDC73B0-0xDC7274 = 0x13C` 恰是已知槽偏移 ⇒ 是同一条 vtable 的两个视图。**
3. **★★★ 一个类可有多条 vtable（多继承）：主 `0xDC7274` / 次 `0xDC7714`，同名槽都在 `+0x13C`。**
