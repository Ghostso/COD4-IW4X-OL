# 201 · 12 字节记录的解码对、用引擎写过的字节锚定、变体选择器归属

## 一、范围

本报告学习 `EngineBindings.cpp` 1587–1766 行。

## 二、`NativeCharacterItemRecord`：12 字节的四段

```cpp
struct NativeCharacterItemRecord {
    std::uint32_t encodedLow{};          // +0
    std::uint8_t  present{};             // +4
    std::array<std::uint8_t,3> padding{}; // +5..7
    std::uint32_t encodedHigh{};         // +8
};
static_assert(sizeof(NativeCharacterItemRecord) == 12);
static_assert(sizeof(NativeCharacterItemRecord) * 12 == 0x90);
```

### 2.1 与反汇编的对应

```text
619ef3  mov dword ptr [ebx+4], 0   ; 高 dword，在 +8   ← encodedHigh
619efa  mov byte ptr [ebx], 0      ; 存在字节，在 +4   ← present
```

**注意 `[ebx]` 在 `[ebx+4]` 之后** —— 因为 `ebx = ecx+4`（目标基址 +4），所以：
- `[ebx]` = `ecx + 4` = **present**
- `[ebx+4]` = `ecx + 8` = **encodedHigh**
- 而 `esi = ebx - 4` = `ecx + 0` = **encodedLow**

**条目基址 `ecx + 12k`，而不是 `ecx + 4 + 12k`** —— 注释里那句"`esi = [ebx-4]` 条目 BASE 是 目标 + 12k"正是这个。

### 2.2 那条 `==` 而不是 `<=`

```cpp
// == and not <=. The three carried numbers section 59 and section 60 found all
// survived a bound, because every value smaller than the answer satisfies one.
static_assert(sizeof(NativeCharacterItemRecord) == 12);
```

**"每一个小于答案的值都满足一个界"** —— 与 §148 里 `19 + 18 == 37` 同一条纪律，这是本项目第四次出现同一句论证。

## 三、那个"两个缺陷是同一个缺陷"

> **一个八字节的记录没有地方放低 dword，所以从它出发任何正确的解码都不可能——两个缺陷是同一个缺陷。**

```text
缺陷 1：数组步长 8 而不是 12 ⇒ 写越界 48 字节
缺陷 2：没有 encodedLow 槽位 ⇒ 解码不可能正确
```

**步长错与解码错不是两件事** —— 它们都源于"这个记录是 12 字节而非 8"。

## 四、解码与编码：三操作数 XOR

### 4.1 解码

```cpp
return std::rotl(decodeKey ^ record.encodedLow ^ record.encodedHigh, 8);
```

对照反汇编（`0x619f20`）：

```text
ROL32(dword_E4DD90 ^ *(dword*)entry ^ *(dword*)(entry + 8), 8)
```

**三个操作数**：

```text
dword_E4DD90     ← 全局键（RVA 0xA4DD90，见 §186）
*(dword*)entry   ← encodedLow
*(entry+8)       ← encodedHigh
```

注释：

> **上一版把键与一个 dword XOR 再旋转，那是 3.3.3.3 的形状，在这里不可能对——它读的那个记录【没有第二个 dword 可 XOR】。**

**又一次"形状对、数字错"** —— 而这次是"结构的形状"。

### 4.2 编码：为什么不需要逆向

```cpp
record.present = 1;
record.encodedLow = 0;
record.encodedHigh = std::rotr(itemId, 8) ^ decodeKey;
```

推导（注释给出）：

> 令 `encodedLow = 0`，解码就化简成 `ROL32(key ^ encodedHigh, 8) == id`，
> 所以 `encodedHigh = ROR32(id, 8) ^ key`，**运行时什么都不必反转**。

**验算**：

```text
decode = ROL(key ^ 0 ^ encodedHigh, 8)
       = ROL(key ^ ROR(id,8) ^ key, 8)
       = ROL(ROR(id,8), 8)
       = id  ✓
```

**两个 key 抵消** —— 所以这个编码只要 key 正确，任何 id 都能往返。

### 4.3 为什么不调 `sub_810B20`

> **`sub_810B20` 是引擎自己的写入者，会做同样的事。这里不调它是因为它从 EAX 和 ESI 取参数，而这里不需要它：一个条目、一个 dword，而算术由 `decodeCharacterItemId` 在单元测试里往返检查。**

## 五、**用引擎写过的字节做锚点**

这是本组最重要的一段方法论。

### 5.1 那条规则

```cpp
// AND IT IS PINNED TO A DWORD THAT WAS MEASURED, NOT TO ITSELF. Section 51j's rule
// is that a symmetric round trip passes even when both sides are wrong, so
// asserting encode-then-decode would prove nothing about either.
```

**"对称的往返即使两边都错也会通过"** —— 所以"编码后有解码能还原"**什么也证明不了**。

### 5.2 三个锚点

```text
0x5FCE6C73  是 manager+0xFB2 处那个字面的 dword，
            在 C:\Games\OLfinal\codol_1649370_full.bin
            —— 【一个真实客户端的记录】
0x7ECE6C71  是同一 profile 的混淆 key，来自 manager+0x11138
【客户端写了那些字节；这个树里没有任何东西写过。】
```

### 5.3 三条 static_assert

```cpp
static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).encodedHigh == 0x5FCE6C73u);
static_assert(encodeCharacterItemId(686u, 0x7ECE6C71u).encodedHigh == 0xD0CE6C73u);
static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).encodedLow  == 0u);
static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).present     == 1u);
```

**验算第一行**：

```text
ROR(545, 8) = 545 >> 8 | 545 << 24
545 = 0x221, 545 >> 8 = 0x2, 545 << 24 = 0x21000000
      = 0x21000002
^ 0x7ECE6C71 = 0x21000002 ^ 0x7ECE6C71
0x21 ^ 0x7E = 0x5F  ✓ (高字节)
0x00 ^ 0xCE = 0xCE
0x00 ^ 0x6C = 0x6C
0x02 ^ 0x71 = 0x73
= 0x5FCE6C73  ✓
```

**完全吻合。**

### 5.4 那条"值得多少"的自评

```cpp
// The pair is consistent as well, which is worth exactly what section 51j says it
// is worth -- nothing on its own, and something once the line above anchors one
// side of it to a byte the engine wrote.
static_assert(
    decodeCharacterItemId(encodeCharacterItemId(2127u, 0xA5A5A5A5u), 0xA5A5A5A5u) == 2127u);
```

**"单独一文不值，而一旦上面那行把一侧锚定到引擎写过的字节，它就有了价值"** —— 这是对"对称往返"最精确的定位。

### 5.5 工具的第三方确认

> `Tools/olfinal/decode-profile-blob.py --path "characterClasses[0].slots[0]"`
> **从那些字节里读回 545。**

## 六、`characterModelResolutionEnabled()`：一个能满足退出条件的门

### 6.1 状态

```text
OLMOD(section-67-resolution-gate): ON BY DEFAULT SINCE SECTION 69
```

### 6.2 为什么曾经关

> **它关了一个小节，而理由是测出来的**：开着解析时，最初两次活体运行产出五个正确槽的名字，**然后在随后的 DObj 构建里 FAULT，报 `op=8 target=0x00000000` 以及一个被污染的镜像**，
> **而它替换的桩更早、更干净地失败，而且仍然让玩家出生。**
>
> **那在当时是正确的决定、错误的诊断：故障是十个未移植的回调槽（§69），不是这条路径。**

### 6.3 移植后同一次运行的输出

```text
character models RESOLVED entity=0 characterItem=545 variant=2 count=5
  record=545,532,525,529,1099,115,-,-,-,-,-,-
player DObj rebuild entity=0 selectionChanged=1 dobjMissing=1
native server player DObj active entity=0
```

然后：

```text
1113 个快照 @20/s，dropped=0 frameReject=none:0，没有任何 fault，
唯一的拒绝是那个记录在案的每次连接一次的 think sync。
```

**退出条件的**两半**在同一次运行上測到**：

1. DObj 构建存活；
2. 记录与 `CodolCharacterCategoryDump.py --resolve` 相同。

### 6.4 保留为 kill switch 的理由

> **这个开关留作 kill switch —— `OLMOD_RESOLVE_CHARACTER_MODELS=0` 恢复桩 —— 因为这是那条决定"玩家到底能不能被打中"的路径（§55），而一个不用重编译就能关掉的途径值一次 `getenv`。**
>
> **任何不是 "0" 的值都保持它开着，所以某人环境里一个陈旧的 "=1" 仍然意味着它以前的意思。**

**默认语义的设计**：`size < 2` ⇒ 开；`value[0] != '0'` ⇒ 开。所以 `"0"` 是唯一的关。

## 七、变体选择器：从"常量"到"线的函数"

### 7.1 第一次活体运行的两个错名

```text
name 0  fpa_goose_ss_m_11          期望 fpa_infbasea 族
name 1  boo_empty_ss_s             期望 boo_infbasea 族
name 2  fja_infbasea_tf_m_wht_00   对
name 3  han_infbasea_tf_m_00       对
name 4  hea_socomb_sc_m            对，且精确
```

> **三个不是 `_ss_` 的里面有两个 `_ss_`，是一次变体分裂**，所以这个值值得一轮，而不是再一轮争论。

### 7.2 §166 用客户端而不是用一轮定下来了

```text
CG_SetupClientCharacterInfo 0x00541800 从本服务器发送的 clientState 构建解析器的请求，
并放 `*(int*)(clientState + 0x154) + 1` —— 【阵营字段加一】——
然后交给对局内解析器 0x0080E600，它的 0x0080E110 支把它用作 sub_61B6C0 的第四个参数。
```

结论：

> **所以选择器根本不是自由常量：客户端从本服务器放到线上的阵营推导它，而这里的任何其它值都会解析出一个客户端永远不会要的角色。**

### 7.3 那次双方分歧的具体表现

```text
它是 2 而线上带 faction 0 时，
两侧在【每一个携带阵营的名字上】都不一致：
    dedicated 构建并 precache 了 fpa_goose_ss_m_11 / fja_infbasea_tf_m_wht_00
    而客户端自己的 characterInfo 持有 fpa_goose_ss_m_15 / fja_infbasea_sc_m_wht_00
```

**`_m_11` vs `_m_15`、`_tf_` vs `_sc_`** —— 阵营和变体都不同。

### 7.4 环境覆盖为什么保留

> **环境覆盖保留，因为测量它仍然值一轮——它只是不再决定那个值。**

```cpp
int characterVariantSelector(faction) {
    if (const auto forced = characterVariantSelectorOverride(); forced) return forced;
    return (int)faction + 1;
}
```

**"唯一决定它的地方"** —— 所以 dedicated 不能再与客户端漂移。

## 八、关键结论

1. **`==` 不是 `<=`**，因为"每个更小的值都满足一个界"——本项目第四次同一句论证。
2. **步长错与解码错是同一个缺陷**：八字节记录没有地方放低 dword。
3. **`encodedLow = 0` 让两个 key 抵消**，所以编码不需要求逆。
4. **对称往返即使两边都错也会通过** ⇒ 必须锚定到**引擎写过的字节**。
5. **门控的默认值要设计**：`"0"` 是唯一关，其余全开（包括陈旧值）。
6. **选择器不是常量而是线的函数** —— 从 `faction + 1` 推导。

## 九、未闭合点

- `sub_810B20` 的真实参数（EAX + ESI）未在本组展开。
- `EngineBindings.cpp` 1766 行之后未读取。
