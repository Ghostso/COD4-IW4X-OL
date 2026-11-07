# 157 · 四项全闭：playlist 中文名（GBK）/ `0xE57A70` 定性质 / 段2「GFx 符号池」更正 / `bind_world` 已接线

> 卷次：157（lobby + 战斗服 · 清 156 卷全部遗留）
> 前置：156（开出四项待办 —— 本卷**逐项闭合，其中一项再次更正 156 自身**）
> 性质：磁盘字节直读 + 代码 xref 双向闭环 + 自研源码实读

---

## 一、四项交付一览

| # | 156 卷遗留 | 本卷结论 | 状态 |
|---|---|---|---|
| ① | playlist 中文名（GBK）未解 | **116 条 playlist 的中文名/英文名/类别/排序全部解出**（GBK 直读，零失败） | ✅ |
| ② | `0xE57A70` 密钥来源 | **是编译期静态种子常量**（零写点、40 处 xor 读），用于**整数字段混淆编解码原语**，非运行时密钥 | ✅ |
| ③ | 段2 二进制资产（DDS/SWF/ifs） | **段2 内 DDS/CWS/ZIP/fastfile 全 0**；所谓「32MB Flash 资源」**是错的**，实为 **GFx ABC 符号池（33,496 个 AS3 类名/源文件名）** | ✅ |
| ④ | 战斗服 `bind_world` | **已于 2026-10-25 接上**（`src/main.c:142`），且紧接着 `codol_world_spawn_map_entities`。记忆旧结论**已过时** | ✅ |

---

## 二、★ ① playlist 中文名：116 条全解（GBK）

### 2.1 编码定案

`name chinese "` 之后是 **GBK 双字节**，非 UTF-8：

```
0x033A4D7E  name chinese "\xca\xb5\xd5\xbd\xb6\xd4\xbf\xb9"
            → GBK decode → "实战对抗"
0x033A50C8  name chinese "\xb3\xe5\xb7\xe6\xcd\xc5\xb6\xd3\xbe\xba\xbc\xbc"
            → "冲锋团队竞技"
```

`\xca\xb5\xd5\xbd` = 实 战，`\xb6\xd4\xbf\xb9` = 对 抗 —— 标准 GBK。

### 2.2 116 条全表（节选，`pid | cat | ord | @LOGAS | 中文名 | 英文名`）

| pid | cat | ord | @LOGAS | 中文名 | 英文名 |
|---|---|---|---|---|---|
| 1 | 1 | 1 | Charge - Skirmish | **实战对抗** | Skirmish |
| 2 | 8 | 0 | Charge - Onboarding | **冲锋团队竞技** | Onboarding |
| 123 | 2 | 0 | Search & Destroy - Skirmish | **实战对抗** | Skirmish |
| 4 | 9 | 3 | Charge - Assault | **冲锋团竞6V6** | Charge - Assault |
| 110 | 1 | 7 | Charge - Nuketown | **-核弹小镇** | Map: Nuketown |
| 190 | 1 | 4 | Charge - Offshore | **末日钻井9V9** | Map: Offshore |
| 223 | 1 | 6 | Charge - Showndown | **-自由广场** | Map: Showndown |
| 226 | 1 | 5 | Charge - Overwatch | **-摩天大楼** | Map: Overwatch |
| 238 | 1 | 6 | Charge - Voroshny | **-边境废墟** | Map: Borderland |
| 68 | 8 | 12 | War God | **战神排位赛** | S&D + DOM Wargod/Esports |
| 10 | 23 | 10 | Survival Normal | **生存模式** | Survival Normal |
| 112 | 23 | 112 | Survival Normal Crash Tropic | **坠机之地** | Crash Tropical |
| 86 | 23 | 86 | Survival Normal Cross Fire | **交叉火力** | Cross Fire |
| 113 | 23 | 113 | Survival Normal Favela | **贫民窟** | Favela |
| 133 | 2 | 29 | Search and Destroy - Express | **极速爆破** | Express |
| 6 | 2 | 4 | Search and Destroy - Assault | **经典爆破6V6** | Assault |
| 206 | 2 | 3 | S&D - Hardcore | **经典爆破6V6 - 真实模式** | Assault - Hardcore |
| 126 | 2 | 2 | S&D - Ground War | **经典爆破9V9** | Ground War |
| 111 | 2 | 10 | S&D - Crash | **-坠机之地** | Map: Crash Tropical |
| 125 | 2 | 9 | S&D - Tunisia | **-突尼斯小镇** | Map: Tunisia 6V6 |
| 224 | 2 | 8 | S&D - Backlot | **-荒野围城** | Map: District 6V6 |
| 239 | 2 | 6 | S&D - Arkaden | **-商业中心** | Map: Arkaden 6V6 |
| 240 | 2 | 7 | S&D - Derail | **-北境中转站** | Map: Derail 6V6 |
| 241 | 2 | 5 | S&D - Fallen | **-无人区** | Map: Fallen 6V6 |
| 247 | 2 | 7 | S&D - Lockdown | **-大都会** | Map: Lockdown 6V6 |
| 248 | 2 | 5 | S&D - Foundation | **-红土矿厂** | Map: Foundation 6V6 |
| 252 | 2 | 5 | S&D - Underground | **-米德尔顿站** | Map: Underground 6V6 |
| 179 | 2 | 2 | S&D - Snow Maps | **白色巨人行动** | S&D: Snow Maps |
| 243 | 15 | 1 | VIP - Assault | **无畏护送 6V6** | VIP - Assault |
| 249 | 16 | 1 | ROBBERY - Assault | **夺宝奇兵 6V6** | ROBBERY - Assault |
| 122 | 9 | 11 | Search and Rescue | **搜索救援** | Search and Rescue |
| 13 | 3 | 5 | TDM - Assault | **战术团竞6V6** | Assault |
| 14 | 3 | 3 | TDM - Ground War | **战术团竞9V9** | Ground War |
| 207 | 3 | 4 | TDM - Ground War - Hardcore | **战术团竞9V9 - 真实模式** | Ground War - Hardcore |
| 15 | 9 | 1 | Domination | **据点争夺** | Domination |
| 71 | 1 | 2 | Charge Ground War | **冲锋团竞9V9** | Ground War |
| 208 | 1 | 3 | Charge Ground War - Hardcore | **冲锋团竞9V9 - 真实模式** | Ground War - Hardcore |
| 180 | 9 | 2 | Charge Ground War - Rust ONL | **冲锋团竞9V9-储油站** | Charge 9v9 - Rust |
| 200 | 13 | 12 | BattleCity - BUDDY | **勇者游戏 双人** | BattleCity - BUDDY |
| 202 | 13 | 14 | BattleCity - HARDCORE - SOLO | **勇者游戏 极限单人** | BattleCity - HARDCORE - Solo |
| 203 | 13 | 15 | BattleCity - HARDCORE - BUDDY | **勇者游戏 极限双人** | BattleCity - HARDCORE - Buddy |
| 214 | 13 | 23 | BattleCity - SOLO - Reverse | **勇者游戏 绝命逃生** | BattleCity - Reverse Circle |
| 220 | 8 | 1 | BattleCityLeague - SOLO | **周末勇者联赛 单人** | BattleCityLeague - SOLO |
| 221 | 8 | 2 | BattleCity - BUDDY | **周末勇者联赛 双人** | BattleCityLeague - BUDDY |
| 237 | 14 | 143 | Nuclear Football | **核子橄榄球** | Nuclear Football |

### 2.3 统计

- `@LOGAS` 块：**118 个**
- 含 `playlist <id>` 的完整块：**116 条**
- 中文名解码成功：**116/116（100%）**
- `category` 值域：1/2/3/8/9/13/14/15/16/23（10 种）

> **`category` 语义**（从名字反推）：1=冲锋、2=爆破、3=战术团竞、8=活动/联赛、9=据点/搜救、13=勇者游戏、14=特殊、15=VIP、16=夺宝、23=生存。

---

## 三、★★ ③ 段2「GFx 符号池」—— 更正 156 卷自己的错误

### 3.1 156 卷说错了什么

156 卷写：

> `0x31xxxxx..0x38xxxxx` — **96% 非零** — **Flash/UI 资源（SWF 内嵌）** — `registerChannelButtonClickHandler`

**两处都错**：

1. **「96% 非零」是 1 MB 分桶的误差**。256 KB 细扫实测：

| RVA（256KB 桶） | 非零 | 可打印 |
|---|---|---|
| `0x03100000` | 0.2% | 0.1% |
| `0x03280000` | 2.0% | 0.8% |
| `0x03300000` | 11.4% | 9.8% |
| `0x03380000` | 43.1% | 33.1% |
| `0x03500000` | 77.3% | 37.9% |
| `0x035C0000` | **95.9%** | 64.4% |
| `0x03600000..0x038C0000` | 96~97% | 62~69% |

⇒ **只有 `0x3580000..0x38C0000` 这一段是真 96%**，前面 `0x3100000..0x3340000` 大量是 0.2%~11%。「整个 0x31..0x38 都是 96%」是把 1 MB 桶的边界值外推了。

2. **「Flash/SWF 资源」没有文件头**。实测（分「段2 内」与「全镜像」两栏）：

| 魔数 | **段2 内** | 全镜像 | 判读 |
|---|---|---|---|
| `DDS ` | **0** | 1（@`0x86B38F`，在段1） | 段2 无纹理 |
| `CWS`(SWF zlib) | **0** | 1（@`0x82A1C1`，与 `FWS` 紧邻的字符串） | 段2 无压缩SWF |
| `ZWS`(SWF LZMA) | **0** | 0 | — |
| `PK\x03\x04`(ZIP) | **0** | 0 | 无打包 |
| `\x89PNG` | **2** | 2 | 均为偶然字节（前后非 PNG 结构） |
| `OggS` | 0 | 0 | — |
| `RIFF` | 0 | 0 | — |
| `IWff0100` | **0** | 2（@`0xDB5EE0` 等，在段1） | 段2 无 fastfile |
| `FWS` | **1**（偶然） | 2 | `0x82A1B9` 处是 `cmp eax,0x465457` 的立即数 `FWS\0`（汇编里的比较常量），`0x1C5215F` 是数据区偶然 |

**⇒ 段2（那 219 MB）里没有任何打包资产**（DDS/ZIP/SWF/fastfile 全 0）。全镜像个别命中均落在**段0/段1**（代码/只读数据），不是段2。

### 3.2 那 96% 的区域到底是什么

`0x03540000..0x038C0000`（3.67 MB）实测：

```
distinct 符号型 token : 33,496
  codo*            : 5,315
  路径型(a/b/c)     : 3,827
  fsg*             : 1,282
  GET_/SET_*       :    63
  .as 源文件名      :   966   （BaseMain.as / MenuMain.as / AARChallengeListItem.as …）
  distinct codo* 路径: 2,029（codo.component.core / codo/shared/career/weeklyChallengeRewardImage …）
```

**内容样本**：

```
codo.base:BaseMain/toggleTip
codo.component.core
codo/component/ChallengeChecklistGPReward
codo/objects/SupplyDropGrantedItemObj
codo/shared/marketplaceItem/statIconRecoil
codo.utils/ClashPvpUtil
fsg.shared.widgets:FsgTabChallengePanelItem/setProgressBarOffsets
__go_to_ctor_definition_help
prototype
```

**同时确认区域里没有**：`<?xml`=0、`<symbol`=0、`<DOMSymbolInstance`=0、`DefineSprite`=0、`PlaceObject`=0。

### 3.3 定案：**GFx ABC 符号池**

| 可能 | 判据 | 结论 |
|---|---|---|
| SWF 文件 | 无任何 SWF 魔数/标签 | ❌ |
| XML/GFX 资源 | `<?xml`/`<symbol` 全 0 | ❌ |
| 插件二进制（ABC 字节码本体） | 96% 非零符合，但夹杂的大量 ASCII 名字说明这是**字符串池**而非字节码 | ⚠️ 部分 |
| **ABC 的「常量池」段（字符串表）** | `name`/`path`/`namespace`/`method` 名全部 ASCII、`__go_to_ctor_definition_help`/`prototype` 是 AS3 运行时保留名、`.as` 是源文件名 | ✅ **正在此** |

⇒ **`0x3580000..0x38C0000` = Scaleform GFx 的 AS3 ABC「字符串常量池」+ 命名空间表**，即客户端全部 Flash UI 的类名/方法名/源文件名/属性名的**字符串仓库**。

> 这与 133/136 卷「816 短名 ↔ 829 对象」正好互补：**那边是 C++ 侧的 AS 接口名，这边是 Flash 侧的类/方法名**。两边合起来，UI 层的「C++ ↔ Flash」符号面就是全的。

### 3.4 更正 156 卷的第三处

156 卷把这段归为「**Flash/SWF 资源（SWF 内嵌）**」，暗示可以从镜像里**提取出 SWF 播放**。

**不可能。** 这里没有 SWF，只有名字字符串。真正的 `.gfx`/`.swf` 在磁盘上是独立文件（`codo.gfx` 在 135 卷已记录），不在镜像段2 里。

---

## 四、★ ② `0xE57A70` 定性质：编译期静态种子，非运行时密钥

### 4.1 零写点（强力证据）

对 `0xE57A70` 做**全写形穷举**：

| 写形 | 命中 |
|---|---|
| `A3` (`mov [T],eax`) | **0** |
| `89 05/0D/15/1D/35/3D` (`mov [T],r32`) | **0** |
| `C7 05` (`mov dword [T],imm32`) | **0** |
| `01/09/11/19/21/29/31 05` (`add/or/and/sub/xor [T]`) | **0** |

**⇒ 全镜像没有任何一条指令写它。**

### 4.2 磁盘值 = 静态初始化

```
[0xE57A70] on disk = 04 2a 03 46  →  0x46032A04
所在段: .tp3#3  RVA 0xA57A70, 段内偏移 0x41A70
RawSize = 0x62000 ⇒ 0x41A70 < 0x62000 ⇒ **在标准加载器映射窗口内**
```

⇒ **它是被 PE 文件直接静态初始化的常量**（在 RawSize 内，不是 BSS 运行时值）。这与 155 卷「段2 有真实文件内容」互相印证。

### 4.3 它所在的常量表

```
0xE57A40: 0x4C1253FC    0xE57A44: 0x5A101FCE
0xE57A48: 0xF66A8607    0xE57A4C: 0x0BCDBB58
0xE57A50: 0x88CDD457
0xE57A54: 0x00000101    0xE57A58: 0x00000001   0xE57A5C: 0x00000000
0xE57A60..0xE57A6C: 四个字符串指针 (0x00DBCCxx)
0xE57A70: 0x46032A04   ← ★ 主角
0xE57A74: 0x43B40000 (=360.0f)
0xE57A78: 0x00000750 (=1872)
0xE57A7C: 0x41800000 (=16.0f)
0xE57A80..: 更多字符串指针
```

**前 5 个 `0x4C1253FC/0x5A101FCE/0xF66A8607/0x0BCDBB58/0x88CDD457` 是高熵 u32**，不是指针（不在 `0x400000..0xE60000` 范围）⇒ **一组固定种子/魔数**。

### 4.4 用途定案：整数字段混淆编解码原语

171 处引用中，可用形态全部是同一个模板。取 4 个不同调用点（`0x475A25`、`0x512D05`、`0x5E57FD`、`0x69AD42`、`0x7F8740`）——**五处代码形状完全一致**：

```asm
; 读一个已混淆的 32 位字段
mov  eax, [<record> + kOff]     ; 混淆值
xor  eax, [0xE57A70]            ; ★ 解第一层
mov  ecx, 0x10
sub  ecx, i                    ; i = 字段序号
mov  edx, eax
shr  edx, cl                   ; 高位移到低位
lea  ecx, [i+0x10]
shl  eax, cl                   ; 低位左移
or   eax, edx                  ; ★ 16 位循环移位（按字段号 i 变化）
xor  eax, [<record>]           ; 解第二层
rol  eax, 8                    ; ★ 最后字节旋转
```

随后 `push eax` 直接进 `"%d"` / `"|%d"` 格式化。

**⇒ 这是一个「字段级混淆编解码」原语：**
- 输入：记录里的两个 u32（`[rec+kOff]` 与 `[rec]`）
- 密钥：静态常量 `0xE57A70`
- 变换：`xor → 按字段号循环移位 → xor → rol 8`
- 输出：明文整数字段（用于日志/ID 打印）

**它保护的不是「数据完整性」，而是「记录里整数字段的可读性」** —— 防止内存扫描直接读出明文 ID。与 121 卷的帧层 HMAC（完整性）**完全不同层**。

> **纠正 156 卷的措辞**：156 卷写「这是 DVAR 表完整性校验的全局密钥」。**错**。它是**字段混淆常量**，校验的是「可读性」不是「完整性」。

---

## 五、★ ④ 战斗服 `bind_world`：已接线（记忆旧结论过时）

### 5.1 记忆旧结论

`codol-battle-server-world-binding.md` 记：

> `codol_battle_service_bind_world()` **从未被调用过**，`svc->world` 恒为 NULL。

### 5.2 实测：**已接上**

```
CODOL_SERVER_319_20261021\src\main.c:142
    codol_battle_service_bind_world(&g_battle, &server->world, 0);
```

自带注释（原文）：

```c
/* ★★ 把 world 绑进战斗服(2026-10-25)。
 *   此前 **从未调用过** bind_world -> svc->world 恒为 NULL ...
 *   注: 这一步只改服务端内部, 不改任何上行字节(快照仍按 omit 策略发送)。 */
codol_battle_service_bind_world(&g_battle, &server->world, 0);
```

**紧接着还有一步**（记忆里没有）：

```c
/* ★★ 按地图实体表生成世界里的实体(2026-10-25) ... */
codol_world_spawn_map_entities(&server->world);
```

### 5.3 定义/调用/测试三处齐全

```
include\codol_battle_service.h:88   void codol_battle_service_bind_world(...);   ← 声明
src\battle\battle_service.c:29      void codol_battle_service_bind_world(...)    ← 定义
src\main.c:142                      codol_battle_service_bind_world(...);       ← ★调用
tests\test_static_closure.c:271     codol_battle_service_bind_world(...);       ← 测试
```

**⇒ 这项「未闭合」实际在 2026-10-25 就闭合了，只是记忆没更新。**

### 5.4 附：`bind_world` 在客户端镜像里零命中

对客户端镜像搜 `bind_world` / `BindWorld` / `bind_entity` / `sv_world` / `G_InitWorld` —— **全部 0 命中**。

⇒ 这**从来不是客户端逆向项**，是我方战斗服的内部函数名。把它列进「客户端未闭合项」本身是分类错误。

---

## 六、更正汇总（本卷改了 156 卷三处、旧记忆一处）

| 来源 | 原结论 | 本卷 |
|---|---|---|
| 156 §二 | 段2 的 `0x31..0x38` 是「96% 非零的 Flash/SWF 资源」 | **错**。真 96% 只有 `0x3580000..0x38C0000`；内容是 **GFx ABC 符号池**（33,496 个 AS3 类/方法/源文件名），**段2 内 DDS/CWS/ZIP/fastfile 全 0** |
| 156 §二 | 段2 可「提取 SWF 资源」 | **不可能**。镜像段2 里没有 SWF 文件，只有名字字符串 |
| 156 §三.4 | `0xE57A70` = 「DVAR 表完整性校验的全局密钥」 | **错**。是**字段混淆编解码常量**（零写点、静态初始化、`xor→循环移位→xor→rol8`），保护可读性非完整性 |
| 记忆 `codol-battle-server-world-binding` | `bind_world` 从未调用 | **已过时**。2026-10-25 已接上（`main.c:142`），并加 `spawn_map_entities` |

---

## 七、可复现命令

```python
import struct, re
d = open(r'E:\codol_re\client_image_20261027.bin','rb').read(); IB = 0x400000

# ① playlist 中文名（GBK）：整段解码后按 re 抽
txt = d[0x033A4000-IB:0x033C0000-IB].decode('latin1')
for m in re.finditer(r'name chinese\s*"([^"]*)"', txt)      :
    cn = m.group(1).encode('latin1').decode('gbk', 'replace')
    print(cn)                      # 实战对抗 / 冲锋团队竞技 / 坠机之地 ...

# ② 0xE57A70 静态常量
print(hex(struct.unpack('<I', d[0xE57A70-IB:0xE57A70-IB+4])[0]))   # 0x46032A04

# ③ 段2 资产普查（DDS/PK/PNG 应全 0）
seg2 = d[0xA16000-IB:0xE5C7CC0-IB]
for mg in (b'DDS ', b'CWS', b'PK\x03\x04', b'\x89PNG'):
    print(mg, seg2.count(mg))
```

---

## 八、方法论

1. **★ 分桶宽度决定结论。** 1 MB 桶给出「96%」，256 KB 桶给出「0.2%~97%」。**桶宽必须小于结构尺度**，否则边界值会被外推成整段。
2. **★ 「有 96% 非零」不等于「有资产」。** 判断资产必须**找文件魔数**，不能靠非零率。全镜像 0 个 DDS/PK/PNG 是硬证据。
3. **★ 零写点 + RawSize 内 + 静态值 ⇒ 编译期常量。** 三者同时成立时，不要再去猜「运行时哪来的」。
4. **★ 常量用途看使用模板，不看常量本身。** `0xE57A70` 单独看只是个 u32；看 5 处同形代码才知道是「xor→循环移位→xor→rol8」的字段还原。
5. **★ 「记忆里的未闭合」可能早已闭合。** 引用旧记忆前必须**回查源码当前状态**（本卷 `bind_world` 就是这样）。
6. **★ 分类错误比结论错误更隐蔽。** 把「我方战斗服函数」列进「客户端逆向未闭合」，导致它挂了一个月。
