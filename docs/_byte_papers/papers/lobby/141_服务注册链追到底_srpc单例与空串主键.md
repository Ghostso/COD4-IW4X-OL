# 141 · 服务注册链追到底：srpc 单例、7 张哈希表、空串主键与类型号分配器

> 前序：140（消息类型号定案）、139（房间投递 / 五层注册门）
> 性质：**逐指令逆向 + 单例构造逐字节验证**。本卷补上 140 遗留的「4 字节服务名」缺口，
> 并**推翻 140 §3.4 的一处结论**（`0xDAE091` 不是"空串哨兵导致表为空"，而是**全表统一的主键**）。

---

## §0 十二条结论

1. ★★★★★ **`0xB80D90` 不是"查找"，而是「注册并返回类型号」的完整入口**（8 步：查 → 未找到则新建 → 分配类型号 → 插入 → 查回 → 返回）。
2. ★★★★★ **`dwLobbyImp` 的服务注册表属于 srpc 单例 `[0x8269774]`，不属于 `dwLobbyImp`。**
   所有注册调用点的 `ecx` 都来自 `0x803830` 的返回值。
3. ★★★★★ **srpc 单例的 vtable = `0xD599DC`**（`0xB82173 mov dword [esi], 0xD599DC`）。
4. ★★★★★ **srpc 单例内部有 14 张哈希表**：`+0x08/+0x20/+0xD4/+0xF4/+0x114/+0x12C/+0x144/+0x15C/+0x174/+0x18C/+0x1A4/+0x1BC/+0x1D4/+0x1EC`。
5. ★★★★★ **其中 7 张由 `dwLobbyImp` 侧注册**（偏移与 7 个 helper 精确对应）。
6. ★★★★★ **`srpc+4` = 类型号分配器，构造时初始化为 0**（`0xB82179 mov dword [esi+4], 0`）。
   **每次注册取当前值当类型号**（`0xB80E37 mov ecx,[ebx+4]` → `0xB80E3B push ecx` → `0xB920E0` 存进节点 `+4`）。
7. ★★★★ **全部 68 个注册调用点的名字参数 100% 都是 `0xDAE091`** —— 该地址是**空串 `""`**。
8. ★★★★ **⇒ 每张哈希表里只有 1 个条目，主键是 `""`，值是类型号。**
   140 卷说"名字表静态为空"方向对，但**原因判错了**：不是"没人填"，而是"统一用空键"。
9. ★★★ **`0xB80D90` 内 8 步完整流程**（§3）。
10. ★★★ **`0xB920E0(type_id, name)` = 节点构造器**：`[node+0]=vtable 0xD5A76C`、`[node+4]=type_id`、`[node+8]=名字副本(≤15 字节)`。
11. ★★★ **`0xB80CA0` = 哈希表 clear**（遍历冲突链释放节点、清桶、计数归零），
    其 28 个调用者是 `dwLobbyImp` 的**析构链**（`0xB8258C..0xB82727`，`mov byte [ebp-4],N` 是异常状态号），**不是注册**。
12. ★★ **`0x7F0970` = `dwLobbyImp` 单例构造**（写 vtable `0xDE07A4` + 三个字段清零 + 19 个 0xF8 子对象）。

---

## §1 ★★★★★ 归属更正：注册表属于 srpc 单例

### 1.1 证据：ecx 全部来自 `0x803830`

```asm
0x4B0A50  push ebp / mov ebp,esp / push ecx / push esi
0x4B0A55  call 0x803830          ; → [0x8269774]  (srpc 单例，惰性构造)
0x4B0A5A  mov esi, eax
0x4B0A60  mov ecx, esi ; call 0xB7A670   ; 状态；!=2 则放弃
0x4B0A6C  push 0xDAE091
0x4B0A71  mov ecx, esi           ; ★ ecx = srpc 单例
0x4B0A73  call 0xB814B0          ; 注册 helper
```

`0x4B4E72`、`0x4B2417`、`0x4B24A0` 等 68 个调用点全部是同一形态。

### 1.2 srpc 单例的身份

```asm
0x803830  mov eax,[0x8269774]
0x803837  jne 0x8038A7            ; 已构造则直接返回
0x80383E  call 0xB74220           ; alloc 0x1618
0x80384C  call 0xB82130           ; ★ 构造
0x803851  mov [0x8269774], eax
0x80385B  push 0xE39B6E8
0x803861  call 0xB7A400           ; ★ 把 dwLobbyImp 单例挂到 srpc+0x4F0
```

```asm
0xB82130  srpc ctor
0xB82173  mov dword [esi], 0xD599DC    ; ★ vtable
0xB82179  mov dword [esi+4], 0         ; ★ 类型号分配器 = 0
0xB8217C  call 0xB7FC20                ; 哈希表 ctor（14 张）
```

★ **`0xB82157 mov [ebp-0x10],esi` 保存 this**；`0xB7A400` 的 `mov [ecx+0x4F0], eax`
正是把 `dwLobbyImp` 挂到 `srpc+0x4F0` —— 这与 139 卷的 `[dwLobbyImp+0x4F0]` 是**两个不同对象**，
一个是 srpc 持有 dwLobbyImp，一个是 dwLobbyImp 持有 dwLobbyEventHandler，不能混。

### 1.3 srpc 单例的 14 张哈希表

```
+0x008  +0x020  +0x0D4  +0x0F4  +0x114  +0x12C  +0x144
+0x15C  +0x174  +0x18C  +0x1A4  +0x1BC  +0x1D4  +0x1EC
```

`dwLobbyImp` 侧的 7 个 helper 使用的偏移：

| helper | 哈希表偏移 |
|---|---|
| `0xB80D90` | `+0x18C` |
| `0xB80EC0` | `+0x174` |
| `0xB80FF0` | `+0x1BC` |
| `0xB81120` | `+0x1EC` |
| `0xB81250` | `+0x114` |
| `0xB81380` | `+0x144` |
| `0xB814B0` | `+0x12C` |

**⇒ 7/14 由 `dwLobbyImp` 侧注册，另 7 张由其他模块注册。**

---

## §2 ★★★★ 空串主键（推翻 140 §3.4）

### 2.1 事实

```
helper 0xB80D90 +0x18C  调用者 25  →  名字参数 100% 是 0xDAE091
helper 0xB80EC0 +0x174  调用者  7  →  100% 0xDAE091
helper 0xB80FF0 +0x1BC  调用者  5  →  100% 0xDAE091
helper 0xB81120 +0x1EC  调用者  3  →  100% 0xDAE091
helper 0xB81250 +0x114  调用者 23  →  100% 0xDAE091
helper 0xB81380 +0x144  调用者  4  →  100% 0xDAE091
helper 0xB814B0 +0x12C  调用者  1  →  100% 0xDAE091
```

### 2.2 `0xDAE091` 的实际内容

```
0x00DAE080  6f 67 00 00 7a 6f 6d 62 69 65 5f 61 72 65 6e 61  |og..zombie_arena|
0x00DAE090  00 00 00 00 32 33 33 32 00 00 00 00 32 33 33 34  |....2332....2334|
```
**`0xDAE091` 指向 `""`（空串）。** 前面是 `"zombie_arena\0"` 的结尾，后面是 `"2332"/"2334"/…` 数字串池。

### 2.3 推论

**每张哈希表里只有 1 个条目：key = `""`，value = 类型号。**

这解释了：
- 为什么全镜像搜不到任何 4 字符服务名（**根本不存在名字**）
- 为什么 140 §3.4 的"注册表静态为空"方向对、**原因判错**

★ **140 卷说"名字表静态为空 ⇒ 名字运行时注入"，实际是"每个服务表只存一个空键条目"。**

---

## §3 ★★★★★ `0xB80D90` 完整流程（8 步）

```asm
; ---- 入口 ----
0xB80D90  push ebp / mov ebp,esp / SEH 安装
0xB80DB8  mov ebx, ecx           ; ★ ebx = this = srpc 单例
0xB80DBF  call 0xB7A670
0xB80DC4  cmp eax, 2
0xB80DC7  je  0xB80DE4           ; ★ 状态 != 2 ⇒ 直接返回 0

; ---- 步骤 1：构造 std::string(name) ----
0xB80DE4  mov edi,[ebp+8]        ; ★ edi = name 参数（= 0xDAE091 空串）
0xB80DE7  push edi
0xB80DE8  lea ecx,[ebp-0x14]
0xB80DEB  call 0xB75A50          ; 构造临时 string

; ---- 步骤 2：查哈希表 ----
0xB80DF6  lea esi,[ebx+0x18C]    ; ★ 该服务的哈希表
0xB80DFD  call 0xB7FCD0          ; 查
0xB80E04  test eax,eax
0xB80E09  sete byte [ebp+0xb]    ; ★ 未找到 ⇒ 需要注册

; ---- 步骤 3：分配 0x18 字节节点 ----
0xB80E1F  push 0x18
0xB80E21  call 0xB74220

; ---- 步骤 4：分配类型号并构造节点 ----
0xB80E37  mov ecx,[ebx+4]        ; ★★★ type_id = srpc 单例 +4 计数器
0xB80E3A  push edi               ; 第 2 参 = name
0xB80E3B  push ecx               ; 第 1 参 = type_id
0xB80E3C  mov ecx, eax           ; this = 新节点
0xB80E3E  call 0xB920E0          ; 节点构造

; ---- 步骤 5：插入哈希表 ----
0xB80E5E  mov ecx, esi
0xB80E67  call 0xB7F950

; ---- 步骤 6：查回类型号 ----
0xB80E93  call 0xB80D60
0xB80EA3  mov eax,[ebp-0x10]     ; ★ 返回类型号
0xB80EB7  ret 4
```

### 3.1 `0xB920E0(type_id, name)` 节点构造器

```asm
0xB920E3  mov eax,[ebp+8]     ; type_id
0xB920E6  mov edx,[ebp+0xc]   ; name
0xB920ED  mov [esi+4], eax    ; ★ node+4 = type_id
0xB920F3  mov dword [esi], 0xD5A76C   ; node+0 = vtable
0xB920F9  lea ebx,[esi+8]     ; node+8 = 名字缓冲
0xB9210F  cmp eax,0xF ; 钳制 15
0xB9211C  call 0xC427F0       ; memcpy(名字, ≤15)
0xB92124  mov byte [edi+ebx],0
```

**节点布局：`[0]=vtable 0xD5A76C`、`[4]=type_id`、`[8..0x17]=名字(≤15 字节)`。**

---

## §4 ★★★ 类型号分配器

```asm
0xB82130  srpc ctor
0xB82179  mov dword [esi+4], 0        ; ★ 初始 0
```
```asm
0xB80E37  mov ecx,[ebx+4]             ; ★ 每次注册读当前值
```
**⇒ 类型号 = 注册序号（第 1 个注册得 0，第 2 个得 1，……）。**

★ **注意：本卷没有找到 `[srpc+4]` 的自增指令**（`0xB7A000..0xB8C000` 内 `inc dword [reg+4]` 为 0 处）。
两种可能：
1. 自增在 `0xB920E0` 内部以其它形态完成（但 `0xB920E0` 全文已读完，无 `+4` 写入）
2. **类型号恒为 0**，靠「每张表只有一个条目」来区分服务

★ **倾向 2**：因为每张表只有 `""` 一个键，**同表内不需要区分类型号**；类型号的真实用途
是 `0xB7F950` 插入时存进 `node[0]`，由 `0xB7FAD0` 查表时取回。

---

## §5 ★★ `0xB80CA0` 是 clear，不是注册（纠正 141 早期判断）

```asm
0xB80CA0  mov [ebp-4],ecx
0xB80CAA  cmp [ecx+4], 0 ; jbe 结束   ; 桶数
0xB80CB4  mov esi,[eax+ebx*4]         ; 桶头
0xB80CC0  mov edi,esi ; mov esi,[esi+8]  ; 沿冲突链
0xB80CC8  call 0xB75AC0               ; 释放 string
0xB80CCE  call 0xB74240               ; 释放节点
0xB80CE0  mov dword [edx+ebx*4], 0    ; ★ 清桶
0xB80CEF  mov dword [ecx], 0          ; ★ 计数归零
```

其 28 个调用者（`0xB8258C..0xB82727`）全部是 `lea ecx,[esi+0xNNN]` + `mov byte [ebp-4],N`
（N 从 0 到 0xE 递减）—— 这是 **`dwLobbyImp` 析构链**的异常状态号，不是注册。

---

## §6 ★★ `dwLobbyImp` 单例构造（`0x7F0970`）

```asm
0x7F0973  mov ecx, 0xE39B6E8
0x7F0978  call 0xB965D0                ; 基类构造
0x7F097F  mov dword [0xE39B6E8], 0xDE07A4   ; ★ vtable
0x7F0989  mov dword [0xE39B6EC], 0     ; +4 = 0
0x7F098F  mov dword [0xE39B6F0], 0     ; +8 = 0
0x7F0995  mov dword [0xE39B6F4], 0     ; +0xC = 0
0x7F099B  mov esi, 0xE39B6F8
0x7F09A0  lea edi,[ebx+0x13]           ; 19 次
0x7F09A7  call 0xB97F20                ; 构造 0xF8 子对象
0x7F09AC  add esi, 0xF8
0x7F09B5  push 0xE39CA58 ; ...         ; 两个 0x1F4×0xC8 表
0x7F09EB  mov eax, 0xE39B6E8           ; ★ 返回单例
```

---

## §7 完整注册链（终稿）

```
网络/模块初始化
  └ 0x803830  srpc 单例（惰性）
      └ 0xB82130  srpc ctor
          ├ vtable = 0xD599DC
          ├ +4 = 0（类型号计数器）
          ├ 14 张哈希表（+0x08..+0x1EC）
          └ 0xB7A400: srpc+0x4F0 = dwLobbyImp 单例
                          │
  └ 68 个注册调用点（ecx = srpc 单例, name = 0xDAE091 "")
      └ 0xB80D90 / 0xB80EC0 / 0xB80FF0 / 0xB81120
         / 0xB81250 / 0xB81380 / 0xB814B0
          ├ 0xB7A670 状态 == 2
          ├ 0xB7FCD0 查
          ├ 0xB74220 分配 0x18 节点
          ├ 0xB920E0 构造（type_id = [srpc+4], name）
          ├ 0xB7F950 插入哈希表
          └ 0xB80D60 查回 → 返回类型号
                          │
  └ 类型号 → 0xB7FAD0 的 FNV-1a 查表 → 0xB83744 表（类型号-1 索引）→ handler
```

---

## §8 诚实边界

1. **`[srpc+4]` 的自增点未找到**。全文扫 `inc dword [reg+4]` 在 `0xB7A000..0xB8C000` 内 0 命中；
   `0xB920E0` 全文无 `+4` 写入。**倾向"类型号恒为 0"**，但未证死。
2. **srpc 单例的 RTTI 名未取到**（`0xD599DC-4` 落在段2 空洞，读为 0）。
3. **`+0x08/+0x20/+0xD4/+0xF4` 四张表由谁注册未追**（只确认了 `dwLobbyImp` 侧的 7 张）。
4. **"空串主键"如何区分 68 个服务**：由于每张表独立，同表内只有 1 个条目 ⇒ 不需要区分；
   但**跨表**如何路由到正确的 helper，取决于调用点选择的表偏移，**这一点已闭合**（§1.3）。
5. **`0xDAE091` 在别处被用 8944 次**，其中 3165 次是 `push`；本卷只分析了注册相关的 68 次。

---

## §9 工具

| 工具 | 用途 |
|---|---|
| `tools/s141a_sentinel.py` | 哨兵字节与调用点上下文 |
| `tools/s141j_fix.py` | **修正版**：只取 call 前 8 字节内的 push imm32 |
| `tools/s141i_allhelpers.py` | 7 个 helper 全量对照 |
| `tools/s141q_srpccls.py` / `s141r_srpcvt.py` | srpc 单例身份与哈希表偏移 |
| `tools/s141t_inc2.py` | 类型号自增点搜索（0 命中） |
| `tools/as_show_135.py` | 反汇编器 |

## §10 方法论

1. ★★★★★ **「调用者参数全是同一个常量」不是"没人填"，而是"统一用默认值"** —— 先确认那个常量是什么。
2. ★★★★ **`ecx` 的来源决定 this 是谁**：`mov ecx,esi` 而 `esi = call 0x803830` ⇒ this 是单例，不是外层对象。
3. ★★★★ **一个对象可以有 14 张同构哈希表**，靠偏移区分；不要因为"只有一张表"就下错结论。
4. ★★★ **`inc dword [reg+4]` 搜不到时，先怀疑"根本不需要自增"**（每表只有一条）。
5. ★★ **"析构链"与"注册链"长得像**（都是 `lea ecx,[esi+off]` + `call`），
   区别在于**析构带 `mov byte [ebp-4],N` 的异常状态号**，注册带 `push <name>`。
