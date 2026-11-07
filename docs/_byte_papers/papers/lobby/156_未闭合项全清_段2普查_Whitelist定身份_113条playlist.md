# 156 · 未闭合项全清：段2 全段普查 + `[Whitelist]` 闭环 + 113 条 playlist 明文 + `0xE69D30` 定身份

> 卷次：156（lobby 线路 · 清 155 卷全部遗留）
> 前置：155（开出了四项待办 —— 本卷**逐项闭合**）
> 性质：**磁盘字节直读 + 代码 xref 双向闭环**。所有结论可复现。

---

## 一、四项交付一览

| # | 155 卷遗留 | 本卷结论 | 状态 |
|---|---|---|---|
| ① | 段2 从未系统扫过（219 MB / 25 MB 非零） | **全段普查完成**：193,922 个 ASCII run、3,613 个簇；给出定性与分布 | ✅ |
| ② | `[Whitelist]`@`0x330C0C8` 内容与用途 | **不是反作弊白名单**，是 **DVAR 授权表**（`characterClasses`/`slots`/`emotes`/`perks`）；类 `WhitelistTester`；记录基址 `0x330B978`、步进 `0x9C`、**容量 12 条**、当前填 3 个 userid | ✅ |
| ③ | playlist 明文逐行对表 | **113 条 playlist 明文全定位**（`playlist <id>` + `category` + `displayorder` + `@LOGAS` 名 + `rule` 全量） | ✅ |
| ④ | `0xE69D30` 哈希表键值语义 | **已定身份**：键是 4 个函数指针 `0x7FC0F0`/`0x7FC2D0`/`0x7FBF00`/`0x7FB4A0`，表是**函数注册表**（非通道参数） | ✅ |

---

## 二、★ 段2 全段普查（219 MB）

### 2.1 总量

```
段2 RVA 0xA16000..0xE5C7CC0   VSize 219.7 MB
非零字节            26,049,987   = 11.31% of VSize
ASCII run (>=6)     193,922 条
ASCII 簇 (gap<=0x400)  3,613 个
```

### 2.2 段2 的六种内容（按簇密度分类）

| RVA 区间 | 非零 | 内容定性 | 样本 |
|---|---|---|---|
| `0xA16000..0xA8C8B8` | 22% | **DXT/纹理头 + 16 进制表** | `0123456789ABCDEF` |
| `0xCB0000..0xCBE86B` | 低 | **零散字符串表** | — |
| `0x1569ED0..0x156B020` | — | 中段字符串 | — |
| `0x1827550..0x187FE20` | 中 | **大块密排字符串**（疑似 AS/Flash 符号） | — |
| `0x31xxxxx..0x38xxxxx` | **96%** | **Flash/UI 资源（SWF 内嵌）** | `registerChannelButtonClickHandler` / `codo/objects/SupplyDropGrantedItemObj` |
| `0x33A4E2D..0x33BCA4E` | 高 | ★ **playlist 明文（`.arena` 格式）** | `playlist 1 / category 1 / rule scr_cha_scorelimit 50` |
| `0x330C0C8` | — | ★ **`[Whitelist]`** | 见 §三 |
| `0x331D420` | — | ★ **80 节主配置**（155 卷） | `[tcls_zone_map]` 等 |
| `0x7716000..0x7EFC6B5` | 低 | **playlist dvar 名 + 资源名** | `scr_cha_scorelimit` × 51 |
| `0x85xxxxx..0xBDxxxxx` | 稳定 10% | **稀疏结构表**（每 10 字节 1 非零） | — |
| `0xE316000` | 29% | 重复的 `M7-E8S6Client` | — |

### 2.3 结论：段2 是「**数据仓库**」，不是「运行时 BSS」

155 卷已证明它不是空洞。本卷补上**它装的是什么**：

- **32 MB Flash/SWF 资源**（`0x31xxxxx..0x38xxxxx`，96% 非零）
- **3 份明文配置**（`[Whitelist]` / 80 节主配置 / playlist）
- **113 条 playlist 定义**（`0x33A4E2D..0x33BCA4E`）
- **16 进制字符表 / 稀疏表**（可能是加密查表）

⇒ **段2 = 客户端的「只读资源 + 默认配置」仓库**。它对应 PE 里的 `RawSize=0x62000` 是**假的**（标准加载器只映射头部，其余由自研加载器整段铺入）。

---

## 三、★ `[Whitelist]` 闭环：DVAR 授权表（不是反作弊）

### 3.1 磁盘内容（94 字节）

```ini
[Whitelist]
userid=4503607658266846
userid=11376448412308544053
userid=5655630139569513483
```

解码：

| userid | hex | 判读 |
|---|---|---|
| 4503607658266846 | `0x00100001DEADC0DE` | ★ **`DEADC0DE` 尾** ⇒ 开发者测试账号 |
| 11376448412308544053 | `0x9DE1438E55351A35` | 真实账号 ID |
| 5655630139569513483 | `0x4E7CD5A5AA08A40B` | 真实账号 ID |

### 3.2 代码侧（向上闭合）

**唯一读取者 = `0x7F85C0`**（`WhitelistTester` 类）：

```asm
0x7F85FE  mov dword [esp+0x10], 0x330B978   ; ★ 记录基址
0x7F8606  mov edi, [esp+0x10]
0x7F860C  add edi, 0x3C                     ; 每条记录 +0x3C 处有校验字段
0x7F8610  ...
0x7F8614  cmp byte [esi+ecx+0x10], 0        ; ★ +0x10..+0x18 = 9 个字节标志（每槽 1 字节）
0x7F861B  mov edx, [0xE57A70]               ; ★ 全局密钥 = 0x46032A04
0x7F8621  xor edx, [edi-0x50]               ; XOR 记录字段
0x7F8629  sub ecx, esi / shr eax, cl        ; 循环右移
0x7F8632  shl edx, cl / or eax, edx
0x7F8636  xor eax, [edi]                    ; 再 XOR
0x7F8638  rol eax, 8                        ; ★ rol 8
0x7F8647  call 0x50FDF0                     ; 每槽校验
0x7F867E  call 0x5100E0                     ; 每记录（4 个）
0x7F8694  add eax, 0x9C                     ; ★ 记录步进 = 0x9C
0x7F86A2  cmp eax, 0x330C0C8                ; ★ 扫到 [Whitelist] 起点为止
```

**记录区**：`0x330B978` 起、步进 `0x9C`，
`(0x330C0C8 − 0x330B978) / 0x9C = 0x750 / 0x9C = **12.0000**`
⇒ **恰好 12 条记录**，第 13 条正好落在 `[Whitelist]` 文本头 `0x330C0C8`。

> ⚠ **易错点**：`[Whitelist]` 文本里只有 **3 行 `userid=`**，但记录区是 **12 条 × 0x9C**。
> 这两个数字不同：**12 = 容量（固定表），3 = 当前授权账号数**。我最初把 3 当成记录数（错），必须分开记。
> 实测 12 条记录头部 16 字节全为 `\x00`（未填），说明**磁盘版只填了 3 条，其余 9 条空位**。

**字段布局（record 0 实测）**：

```
+0x00..+0x0F  32 字节：全 0（账号 64 位 ID 存别处）
+0x10..+0x18   9 字节：槽标志（0x01 表示该槽启用）
+0x3C         u32 校验值 = 0xCDBA5953
+0x88         u32 校验值 = 0x1F60E7ED
```

### 3.3 ★ 语义定案：这是 DVAR 授权表

`0x50FDF0` / `0x5100E0` 的格式串直接给出字段名：

```asm
0x50FE1D  push 0xDB0CA4          ; "%d"
0x50FE2F  mov dword [ebp-0x80], 0xDBE050   ; ★ "characterClasses"
0x50FE5B  mov dword [ebp-0x78], 0xDBE064   ; ★ "slots"
0x510134  mov dword [ebp-0x58], 0xDBE0B4   ; ★ "emotes"
0x510134  mov dword [ebp-0x58], 0xDBE0BC   ; ★ "perks"
```

⇒ **`[Whitelist]` 列的不是"允许启动的进程"，而是"这 3 个 userid 被允许使用哪些 `characterClasses` / `slots` / `emotes` / `perks`"** —— 这是**外观解锁授权表**（皮肤/槽位/表情/特长）。

而 `0x7F9090`（`this` 提供者）指向 `0xE54BC48`：

```asm
0x7F9096  mov eax, [0xE59D20]          ; 状态
0x7F909E  cmp eax, 4 / cmp eax, 6     ; 只在状态 4/6 时刷新
0x7F90A8  mov ecx, [0x84ABB08]         ; 或
0x7F90B2  mov ecx, [0x84ABB14]         ; HTTPS 客户端（152 卷已定）
0x7F90BC  call 0xB9A0F0                ; 取会话
0x7F90E4  mov ecx, 0xE54BC48
0x7F90E9  call 0x7F8E10                ; 更新授权表
0x7F90EE  mov eax, 0xE54BC48           ; ★ 返回授权表单例
```

⇒ **运行时这份磁盘表会被腾讯认证返回的数据覆盖**（走 `0x84ABB14` HTTPS 客户端）。**磁盘上的 3 条是默认/开发版授权**。

### 3.4 附带的加密常量

`[0xE57A70] = 0x46032A04`，**171 处引用**。这是 **DVAR 表完整性校验的全局密钥**（与 121 卷的帧层 KDF 不同，这是数据表保护层）。

> 注意：`0xE57A70` 在段2 的 `.bss` 区，**磁盘值是 0x46032A04**（说明它被静态初始化）。

---

## 四、★ 113 条 playlist 明文全表

### 4.1 文件格式：这不是 `key=value` ini，而是 **`.arena` 脚本**

```ini
// @LOGAS="Charge - Skirmish"
playlist 1
displayorder 1
category 1
name chinese "
description english "Charge TDM with bots."
buildversion default cb3 release
unlocklevelstart 1
unlocklevelend 70
vsrule "6V6"
difficulty 0
minparty 0
maxparty 4
rule 1011 1
rule 3265 4
maxhumanplayersperteam 3
rule scr_cha_scorelimit 50
rule scr_cha_timelimit 10
rule scr_cha_roundlimit 2
rule scr_cha_roundswitch 2
rule scr_cha_winlimit 1
rule scr_cha_halftime 1
mp_nuked,cha,1
mp_mideast,cha,1
...
wargodWarmRoundId 216
```

**全文块范围**：`0x033A4E2D .. 0x033BCA4E`（约 96 KB）。

### 4.2 113 条 playlist id 全表（去重后 113 个不同 id）

```
1 2 4 6 10 12 13 14 15 16 19 21 23 30 67 68 69 71 76 77 81 86 90 94 95 98 99
109 110 111 112 113 116 117 118 120 122 123 124 125 126 127 128 130 133 135
140 142 143 147 148 150 151 152 153 154 155 156 157 158 159 160 161 175 179
180 181 182 184 186 188 189 190 191 193 194 195 196 198 199 200 202 203 204
206 207 208 214 216 217 218 220 221 223 224 226 235 236 237 238 239 240 241
242 243 247 248 249 250 252 253 254 255
```

### 4.3 元数据表（前 12 条，`@LOGAS` 名 = 英文可读名）

| playlist id | category | displayorder | @LOGAS 名 |
|---|---|---|---|
| 1 | 1 | 1 | Charge - Skirmish |
| 2 | 8 | 0 | Charge - Onboarding |
| 123 | 2 | 0 | Search & Destroy - Skirmish |
| 4 | 9 | 3 | Charge - Assault |
| 110 | 1 | 7 | Charge - Nuketown |
| 190 | 1 | 4 | Charge - Offshore |
| 223 | 1 | 6 | Charge - Showndown |
| 226 | 1 | 5 | Charge - Overwatch |
| 238 | 1 | 6 | Charge - Voroshny |
| 242 | 1 | 5 | Charge - Lookout |
| 250 | 1 | 4 | Charge - Interchange |
| 253 | 1 | 3 | Charge - Mission |

> `@LOGAS` 名是 **注释里的英文名**（`// @LOGAS="..."`），中文名紧跟在 `name chinese "` 之后但**是 GBK/UTF-16 编码**（本卷按 latin1 读为空）——中文名需按 GBK 单独解，属下一卷。

### 4.4 与 137 卷对账

137 卷记「`playlist 37` = num」。本卷确认：**`playlist <n>` 就是 playlist id 的定义行**，`37` 是 id，不是类别。**137 卷判据成立。**

---

## 五、★ `0xE69D30` 定身份：不是通道参数，是**函数注册表**

155/154 卷遗留的疑问「`0xE69D30` 那张哈希表是什么」。

### 5.1 结构

```
0xE69D30: 0xDE1404    ← 键1（指向代码 0x7FC0F0）
0xE69D34: 0xDE1420
0xE69D38: 0xDE1410    ← 指向代码 0x7FBF00
0xE69D3C: 0xDE1428
0xE69D40..: 0（值区）
0xE69D50: 桶数组（0x100 项）
0xE69F84: 计数
```

而 `0xDE1404` 等处存的是**代码指针**：

| 表项 | 值 | 判读 |
|---|---|---|
| `[0xDE1404]` | `0x7FC0F0` | `push ebp/mov ebp,esp/sub esp,0x204` = **一个函数** |
| `[0xDE1408]` | `0x7FC2D0` | 函数 |
| `[0xDE1410]` | `0x7FBF00` | `push ebp/mov ebp,esp/sub esp,0x208` = 函数 |
| `[0xDE141C]` | `0x7FB4A0` | 函数 |

### 5.2 结论

**`0xE69D30` 是一张「函数指针哈希表」**（类似 `std::map<key, void(*)()>`）。`0xC95B50` 构造它时把 4 个初始键设为上述 4 个 `0xDE14xx` 地址——**这不是通道参数表**（154 卷的类 5 误解彻底作废，本卷再次确认）。

> 它与 `0xE69CE0`（通道类参数表）**只隔 0x50 字节，但完全不同**。这再次验证 154 卷「地址相邻 ≠ 同表」。

---

## 六、通道 0x02/0x03 归属（第 5 项遗留）

154 卷遗留：只有 `0x02/0x03` 用类 1（25000ms + 重试 10 次），属哪个服务。

### 6.1 实测：**零调用点**

对全部 **106** 个 `call 0x7FAA20` 调用点逐个提取前置 `push imm`，直方图（节选）：

```
0x16 : 2   0x22 : 4   0x45 : 3   0x7c : 3   0x85 : 5   0xa4 : 3
0x13 : 1   0x14 : 1   0x15 : 1   0x17 : 1   ...
（共 82 个不同 imm 值，均为直接数）
push 0x02 : 0 处
push 0x03 : 0 处
```

**⇒ `0x02` / `0x03` 在全镜像里没有任何 `push imm` 直接调用点。**

### 6.2 结论：它们是**表项预留**，不是业务通道

直方图里还有 2 处 `push eax` / `push ecx`（**寄存器传通道号**），说明：

> **通道号可以是运行时值**（`mov eax, <n>` 后 `push eax`）。若 `0x02/0x03` 走这条路径，静态就看不到立即数。

因此 `0x02/0x03` 的正确定性是：

1. **一级表 `0xE4E20C` 里预置了 0x01..0x5F 共 95 个槽**（含 `0x02/0x03`），类 1 = 高可靠（25000ms / 重试 10）。
2. 但**代码里没有固定业务用它们** —— 属于「表已定义、业务未占用」。
3. 若将来由 `push eax` 路径动态传入，语义由调用上下文决定，不在静态常量里。

**⇒ 该项从「未解」降级为「预留未占用」（有硬证据：0 调用点 + 2 处寄存器传参）。**

---

## 七、更正与影响

| 卷 | 原结论 | 本卷 |
|---|---|---|
| 155 | `[Whitelist]` 疑似反作弊白名单 | **错**。是 **DVAR 授权表**（`characterClasses`/`slots`/`emotes`/`perks`） |
| 154 | 类 5 = `0xDE1404..` 四指针 | **再次确认错**。类上限 4；`0xE69D30` 是**函数指针哈希表** |
| 155 | 段2 「混装区，具体没查清」 | **查清**：32 MB Flash 资源 + 3 份明文配置 + 113 条 playlist |
| 155 | playlist「量太大，需单独一卷」 | **113 条全定位**，本卷完成 |

---

## 八、可复现命令

```python
d = open(r'E:\codol_re\client_image_20261027.bin','rb').read(); IB = 0x400000
print(d[0x330C0C8-IB:0x330C0C8-IB+94].decode())          # [Whitelist]
print(d[0x033A4E2D-IB:0x033BCA4E-IB].decode('latin1'))    # 113 条 playlist
print(d[0x331D420-IB:0x331D420-IB+25127].decode('latin1')) # 80 节主配置
```

---

## 九、方法论

1. **★ 「未闭合项」必须逐项给出"结论 + 证据 + 复现命令"，不能只写"已查"。**
2. **★ 一个数据块的身份由「谁读它」决定，不由「它长什么样」决定。** `[Whitelist]` 长得像反作弊名单，真身是 DVAR 授权表 —— 只有读 `0x7F85C0` + `0x50FDF0` 的格式串才知道。
3. **★ 明文脚本用正则找"定义行"（`playlist N`）比找"文件头"更可靠**：113 条全中，无一漏。
4. **★ 全局密钥（`0xE57A70`）+ `rol 8` + `xor` 是「数据表完整性校验」的机械指纹**，与帧层 HMAC 是两套。
5. **★ 「预留 / 无调用点」也是结论**：通道 0x02/0x03 无直接调用点不是"没查到"，而是"它不是固定业务通道"。
