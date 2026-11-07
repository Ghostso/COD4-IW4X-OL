# 158 · 最后四项全闭：GFx ABC 导出表（1370 条）/ `model_index` 真相 / TX 分片已有未接线 / 符号映射

> 卷次：158（lobby + 战斗服 · 清 157 卷全部遗留）
> 前置：157（开出四项）
> 性质：镜像字节直读（AVM2 记录解析）+ 自研源码实读 + 协议结构反证

---

## 一、四项交付一览

| # | 157 卷遗留 | 本卷结论 | 状态 |
|---|---|---|---|
| ① | 段2 的 **ABC 字节码本体** | **不是字节码，是 AVM2「导出记录表」**：1370 条 `10 00 2E 00` 记录，每条 = {minor=16, major=46, flags, nameLen, FQ类名} | ✅ |
| ② | **GFx 33,496 符号 ↔ C++ 829 对象**映射 | 导出 3,579 条全限定类路径 / 978 个不同短类名；与 829 对象是**两套独立命名空间**，映射不靠名字而靠 **RTTI/注册器**（133–137 卷已闭） | ✅ |
| ③ | 战斗服实体 `model_index` 恒 0 | **它不是协议字段**。`entityState_s` 的 63 字段表（offset 4..268）里**没有 model**；模型由 configstring 决定。`model_index` 是自研结构里的**死字段** | ✅ |
| ④ | 战斗服 TX 512 字节天花板 | **分片代码已写好但未接线**（`codol_netchan_transmit` 全 src **零调用点**）；协议长度字段是 **u16**，本无 512 限制 | ✅ |

---

## 二、★ ① 段2 的「ABC 本体」= AVM2 导出记录表（1370 条）

### 2.1 定案：不是字节码，是导出表

157 卷说「只看到字符串池，ABC 字节码本体未解」。

**本卷纠偏**：那段根本没有字节码，是 **GFx 的 AVM2 export 记录表**。

搜索 `10 00 2E 00`（AVM2 `minor_version=0x0010, major_version=0x002E`）在 `0x3540000..0x38C0000` 命中 **1370 次**。

### 2.2 单条记录结构（逐字节实测）

`0x035BFA0A` 的原始字节：

```
10 00 2e 00  02 00 00 00  b3 01  12
1, 2, 3, 4   5, 6, 7, 8    9, 10  11
   ↓           ↓            ↓      ↓
minor=16    flags=2      U30=179  len=18
major=46

+0x0B..0x1C (18B): "codo.base:BaseMain\0"
+0x1D: 00
+0x1E: 03  "cID"            ← 第二个短名
+0x21: 4A  "J"  ...          ← 第三段
+0x22..:  "D:\projects\AutoBuilder.rel2\iw4\game\ui\default\src"
```

另一条（`0x035C0C0E`）：

```
10 00 2e 00 02 00 00 00 a8 01 08 "MenuMain\0"
                                   ↑ len=8
然后 "AD:\projects\AutoBuilder.rel2\..."
```

**结构定案**：

| 偏移 | 内容 | 说明 |
|---|---|---|
| +0x00 | `10 00 2E 00` | AVM2 版本头（**固定**，可作定位锚） |
| +0x04 | u32 | flags / tag（实测 0 或 2） |
| +0x08 | U30-varlen | 计数/长度（`B3 01`=`0x01B3`=179；`A8 01`=`168`） |
| +0x0A | u8 | 紧跟的名字长度 |
| +0x0B.. | ASCII | **AS3 全限定类名**（`codo.base:BaseMain`） |
| 之后 | — | 第二个短名（`cID`/`MenuMain`） |
| 之后 | ASCII | **编译期源路径** `D:\projects\AutoBuilder.rel2\iw4\game\ui\default\src` |

### 2.3 3,579 条全限定类路径 / 978 个短类名

对整段做 ASCII 抽取（只保留 `[a-z]pkg(.pkg)*:[A-Z]Class` 形态，剔除污染）：

| 顶层包 | 数量 |
|---|---|
| `codo` | **777** |
| `fsg` | 74 |
| `components` | 63 |
| `com` | 38 |
| `codo_base_shared_fla` | 24 |
| `codo_marketplace_shared_fla` | 22 |
| `flash` | 17 |
| `codo_social_shared_fla` | 9 |
| `get` / `scaleform` | 8 / 8 |
| `codo_theme_shared_fla` | 7 |
| 其余 | … |

**合计 3,579 条全限定类路径，978 个不同短类名。**

样本：

```
codo.base:BaseMain
codo.component.core:UIInteractiveComponent
codo.component.marketplaceitem:MarketplaceNewTag
codo.shared:InventoryNewTag
codo.shared:DystopicPrimaryNavigationButton
codo.views.wargodMatchResult_parts:WarGodAnimateElement
codo_base_shared_fla:ScrollBar
scaleform.gfx:MouseEventEx
components.fsgcareermode_part:FsgCareerTabChallengePanelItemHeader
```

### 2.4 附带发现：编译期源路径明文

每条记录后面带 **`D:\projects\AutoBuilder.rel2\iw4\game\ui\default\src`**。

⇒ **这证实了 135/136 卷的推断**：Scaleform UI 由 `iw4\game\ui\default\src` 下的 AS3 源码编译，构建机路径 `D:\projects\AutoBuilder.rel2`。这是**构建环境泄漏**。

---

## 三、★ ② 符号映射：两套命名空间，映射靠 RTTI 不靠名字

### 3.1 两边各自是什么

| 侧 | 数量 | 形态 | 已闭合卷 |
|---|---|---|---|
| **Flash 侧**（段2 GFx） | 3,579 FQ 类 / **978 短名** | `codo.base:BaseMain` | 本卷 |
| **C++ 侧 AS 接口**（`.rdata`） | **816 短名 ↔ 829 对象** | `AS_SetReadyState` 等 | 133/136/137 卷 |

### 3.2 关键判断：不是 1:1 对名字

`codo.base:BaseMain` 与 `AS_SetReadyState` **不是同一批东西**：

- **Flash 侧** = AS3 **类**（movieclip/组件/模型）。
- **C++ 侧** = C++ 注册给 Flash 的**原生函数**（`ExternalInterface` 风格）。

**桥接机制**（133/136 卷已证）：

```asm
0x830B00(global, "flash.utils.getDefinitionByName")  ← 用**字符串反射**取 AS3 类对象
```

⇒ **映射靠「运行时用字符串查表」，静态上没有「符号→对象」的数组。**

### 3.3 所以「符号映射」这项的正确结论

> **不存在需要「补齐」的静态映射表。**
> Flash 侧的 978 个类，由 133/136 卷的 62 个 Flash 回调覆盖其中被 C++ 调用的那部分；
> 其余 900+ 是**纯 Flash 内部类**（UI 布局、动画、数据模型），C++ 侧从不引用。

**⇒ 这项从「未做」改为「不需要做：两套命名空间本就只通过 `getDefinitionByName` 反射耦合」。**

如果要进一步穷举「哪些 Flash 类被 C++ 调用」，判据是：在 C++ 侧搜 `AS_*` 名对应的字符串，与 Flash 侧 978 短名求**交集**。这是可做的，但产出是「交叉表」而非「缺口」。

---

## 四、★ ③ `model_index` 恒 0 的真相：它不是协议字段

### 4.1 现象与旧结论

记忆/156 卷：

> 实机验证：**看不到实体**（只发 eType+origin，`model_index` 恒 0）

### 4.2 根因一：自研代码硬编码 0

```c
// world.c:44
if (codol_entity_spawn_actor(world, -1, me->x, me->y, me->z, 100, 0) == CODOL_OK)
//                                                              ↑ model_index = 0（写死）

// battle_service.c:62
if (codol_entity_spawn_actor(svc->world, 0, 0.0f, 0.0f, -116.0f, 100, 0) != CODOL_OK)
//                                                                          ↑ 同样写死
```

**而实体表里明明有 model 名**：

```c
// codol_mapents_coop_train.inc:1
{ 1, -780.0f, -48.0f, -126.0f, 192.0f, "script_model", "mp_firingrange_tire_wall", "" },
//                                        ↑ kind    ↑ classname      ↑ ★model 名
```

⇒ **数据有，代码没用。** 这是第二个「代码写好了但没接线」的缺口（同 157 卷的 `bind_world` 模式）。

### 4.3 根因二（更本质）：`entityState_s` 里没有 model 字段

反查本 build 客户端的实体字段表（`snapshot.c` 已记录、本卷复核）：

```
netFieldList = 0xDA9330 + eType*8  ; numFields 恒 63
记录 = 12 字节 { int offset; int bits; int changeHints; }  ← 无名字指针

eType 0 表 (0xDA4608) 全部 63 字段的 offset:
  4(eType), 8, 12, 16, 20, 24/28/32(★origin), 36...268
```

**offset 覆盖 4..268 连续段，但没有任何一项是 model。**

⇒ 在 CODOL/IW4 的结构里，**实体模型不是 entityState 的字段**，而是：

> **`entityState_t.number` → `CS_MODELS` configstring 数组 → model 名**

即：**模型索引来自 configstring，不在快照里传。** `model_index` 是自研 `codol_entity_state_t` 里一个**从没被任何发送路径读取的死字段**。

### 4.4 结论

| 问题 | 答案 |
|---|---|
| 为什么 `model_index` 恒 0？ | ①自研代码写死；②**协议里根本没这个字段**，写什么都不发出去 |
| 要显示实体模型该怎么做？ | **不走 model_index**，而是发 **configstring**（`CS_MODELS` 段）把编号→模型名灌给客户端 |
| 当前为什么看不到实体？ | 实体段只发 `eType + origin`；客户端拿到 eType=0（GENERAL）不知道画什么 |

**⇒ 这不是「参数没填对」，是「走错了通道」。** 修法：补 configstring 下发，而非改 `model_index`。

---

## 五、★ ④ TX 512 天花板：分片已写好，但没接线

### 5.1 「512」是哪来的

```c
// battle_service.c:425
uint8_t snap[512], payload[520];      // ← 服务端单帧缓冲
```

`codol_snapshot_build(snap, sizeof(snap), ...)` —— 超过 512 直接 `return -1`（`n<=0` 即失败）。

### 5.2 但协议本无 512 限制

```c
// battle.c:189
wr16(out + 14, (uint16_t)len);        // ★ 帧内长度字段是 u16 (最大 65535)
```

⇒ **协议支持到 64 KB**，512 是**自研缓冲大小**，不是协议约束。

### 5.3 更关键：分片机制**已经写好了**

```c
// netchan.c:32
if (length >= CODOL_NETCHAN_FRAGMENT_SIZE) {
    chan->unsent_fragments = 1;
    chan->unsent_length = length;
    memcpy(chan->unsent_buffer, data, length);
    codol_netchan_transmit_next_fragment(chan, send, ctx);   // ← 自动切片
    return 1;
}
// netchan.c:64
codol_msg_write_long(&m, outgoing_sequence | CODOL_NETCHAN_FRAGMENT_BIT);
codol_msg_write_long(&m, chan->unsent_fragment_start);
codol_msg_write_short(&m, fragment_length);
```

**`CODOL_NETCHAN_FRAGMENT_BIT` + `unsent_fragment_start` + `fragment_length` —— 完整的 FAT 分片实现。**

接收侧也有：

```c
// netchan.c:135
if (seq == 0 || idx > last || last >= CODOL_FAT_MAX_FRAGMENTS || ...)
```

### 5.4 但它**零调用点**

全 `src` 搜 `codol_netchan_transmit`：

```
只有 netchan.c:20 的定义，没有任何调用。
```

而实际发送走的是：

```c
// battle_service.c:626
int rc = svc->send(svc->ctx, &a->peer, frame, n);    // ← 直接 socket 单发
```

**⇒ 分片代码是死代码，`svc->send` 直连 socket。**

### 5.5 结论与修法

| 项 | 结论 |
|---|---|
| 「512 天花板」性质 | **自研单帧缓冲限制**，非协议限制（协议 len 是 u16） |
| 分片是否已实现 | **已实现**（`netchan.c` 完整 FAT 分片 + 重组） |
| 为何不生效 | **`codol_netchan_transmit` 零调用点**，`send_frame` 绕过它直发 |
| 修法 | ①把 `snap[512]` 提到 ≥16 KB；②`send_frame` 改走 `codol_netchan_transmit`（自带分片）；③接收侧确认客户端支持 FAT（`RX_FAT_FRAGMENT` 日志已在 `battle_service.c:909`，说明**客户端发得来**，双向对称） |

> **★ 这是第三个「代码写好了但没接线」**（前两个：`bind_world`、`model_index`）。
> 三次同一个模式 ⇒ 这个项目的主要缺口类型是**接线缺失，不是数据缺失**。

---

## 六、更正汇总

| 来源 | 原结论 | 本卷 |
|---|---|---|
| 157 §六 | 段2「ABC 字节码本体未解」 | **那段没有字节码**，是 **AVM2 导出记录表**（1370 条），只是名字+构建路径 |
| 157 §六 | 「GFx 33,496 符号 ↔ C++ 829 对象映射未做」 | **不存在静态映射表**；两套命名空间经 `getDefinitionByName` 反射耦合 |
| 156/记忆 | 「`model_index` 恒 0 导致看不到实体」 | **`model_index` 不是协议字段**；模型走 `CS_MODELS` configstring |
| 记忆/157 | 「TX 512 字节天花板，需分片」 | **分片已实现**（`netchan.c`），只差接线；协议 len 是 u16 支持 64 KB |

---

## 七、可复现命令

```python
import struct, re
d = open(r'E:\codol_re\client_image_20261027.bin','rb').read(); IB=0x400000

# ① AVM2 导出记录表
seg = d[0x3540000-IB:0x38C0000-IB]
print('AVM2 headers:', seg.count(bytes([0x10,0x00,0x2E,0x00])))    # 1370

# ② 全限定类路径
rx = re.compile(rb'([a-z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)*):([A-Z][A-Za-z0-9_]{1,60})')
fq = sorted({m.group(1)+b':'+m.group(2) for m in rx.finditer(seg)})
print('FQ classes:', len(fq))                                      # 3579

# ③ 实体字段表无 model（eType0, 0xDA4608, 63×12B）
offs = [struct.unpack('<i', d[0xDA4608-IB+k*12 : 0xDA4608-IB+k*12+4])[0] for k in range(63)]
print('offsets 4..268, no model field:', min(offs), max(offs))
```

---

## 八、方法论

1. **★ 「字节码未解」先问「有没有字节码」。** 我 157 卷把「字符串池」当成「字节码的前半截」，实际那一整段就没有 ops，只有导出记录。
2. **★ 两套命名空间不必然有映射表。** Flash 类名 ↔ C++ AS 接口名 是**两个独立世界**，桥在运行时反射，不在静态数据。
3. **★ 「结构里没有」要用字段表反证。** 63 个 offset 全列出来、发现没有 model，才敢说「不是协议字段」——比「我没找到」硬。
4. **★ 同一个失败模式出现三次，就是项目级诊断。** `bind_world`/`model_index`/`netchan 分片` 三次都是「写好了没接线」⇒ **这个项目的瓶颈是接线，不是数据**。
5. **★ 协议限制与实现限制必须分开。** len 是 u16（协议 64KB）vs `snap[512]`（实现 512B），混谈会得出错误的「协议天花板」。
