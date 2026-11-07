# 03_DECODER_SEMANTICS

**核心工作包 B:** 建立客户端解码器的实际语义边界。
**镜像:** S-IMG `17cef6e0…f045`(ImageBase `0x400000`,`file_off == RVA`)。
**纪律:** 严格区分 `通用缓冲区解码能力 ≠ 游戏消息解析器 ≠ 具体业务消息处理器`。

---

## 0. 保留的 043/044 修正(全文遵守)

| 编号 | 修正 | 本任务状态 |
|---|---|---|
| M-1 | `0x87A890` 是**长度编码 writer**,不是 reader | 遵守(**未**分析为 reader) |
| M-2 | `0x744B20` 恒返回 1 ⇒ 依赖其结果的 discriminator 分支**不能**作类型证据 | 遵守 |
| M-3 | `0x87C110` 与 `0x87D5A0` **不能**仅因宽度分支相似就认定互相调用/同协议 | 遵守(本任务用调用者与字符串独立判归) |
| M-4 | 已观察 `{0,1,21,22}` 分支**不是**完整类型枚举 | 遵守 |
| M-5 | 21/22 等字段的字符串语义无直接证据前保持**推断** | 遵守 |
| M-6 | 本分析只支持"在该映像覆盖范围内观察到什么" | 全文声明 |

---

## 1. 汇总表

| RVA | 函数边界 | 直接调用者(E8) | 参数 | 返回 | 写入目标 | 实际语义 | 等级 |
|---|---|---|---|---|---|---|---|
| `0x87C110` | `0x87C110` … `0x87D52x`(入口 `__chkstk 0x17F4`) | `0x85D49D`(TQOS) | `arg1`=描述符对象(`[ebp+0x10]` 非空);`arg2`/`arg3`=`{data,len}` 指针;`arg4`=上限 | `>=0` 成功 / `<0` 失败 | `arg1` 对象;`0x400` 诊断 scratch | **TDR net-buffer 解包(路径1)** | DIRECT_STATIC |
| `0x87D5A0` | `0x87D5A0` … `0x87ED1F`(入口 `__chkstk 0x180C`) | `0x85D3DB`,`0x85D418`,`0x85D9B5`,`0x85D9F7`(全 TQOS) | 同左,双 `{data,len}` 对 | `>=0` / `<0` | 同上 | **TDR net-buffer 解包(路径2)** | DIRECT_STATIC |
| `0x87ED70` | `0x87ED70`…`0x87EDA4` | **43** 个(全部 `0x87Cxxx`/`0x87Dxxx`/`0x87Exxx`) | 无 | `eax` = 线程局部 `0x400` scratch 基址 | — | **TDR 诊断 scratch 获取器** | DIRECT_STATIC |
| `0x87EDB0` | `0x87EDB0`…`0x87EDCE` | `0x87C9B7` | `(wchar_ptr, max)` | `eax` = 有界 `wcslen` | — | **有界宽字符长度** | DIRECT_STATIC |
| `0x879AC0` | `0x879AC0`…`0x879D8C` | `0x8799BC`,`0x879D60`,`0x879F44`,`0x87A1F7` | `(host_base, count, out, cap, type)` | 状态码(6/16/0) | 输出缓冲 `edi` | **TDR 变长长度前缀写入器**(`0x80/0x81/0x82/0x83` 前缀) | DIRECT_STATIC |
| `0x87BE00` | `0x87BE00`…`0x87BF4x` | `0x87BA50`(jmp) | `(socket, buf, len, timeout_ms)` | recv 长度 / `-1/-2/-3` | 调用者缓冲 | **`select` 超时门控 + `recv`** | DIRECT_STATIC(045) |
| `0x87BA50` | `0x87BA50`(单条 `E9`)…`0x87BE00` | `0x85D96E`(TQOS recv),`0x85E71A`(TQOS dispatch) | 转发 | 转发 | 转发 | **`jmp 0x87BE00` 跳板** | DIRECT_STATIC |

---

## 2. `0x87C110`(TDR 解包路径 1)

### 2.1 边界与调用者

- 入口 `0x87C110`:`mov eax,0x17f4; call 0xC43280`(`__chkstk`),即**约 6.1 KB 栈帧**的叶子级解包器。
- 直接调用者仅 `0x85D49D`(E8),位于 **TQOS `0x85D430`(QOS 包→网络字节)** 内。
- **无**绝对 dword 引用(函数指针表)指向它(044 `04_INDIRECT_CALL_SCAN.tsv` 复核一致)。

### 2.2 参数 / 返回 / 数据宽度

```
0087c12a  mov ebp,[esp+0x1800]   ; arg1 = 描述符对象
0087c132  mov esi,[esp+0x180c]   ; arg3
0087c13a  mov edi,[esp+0x180c]   ; arg4(经 push 调整后)
0087c162  cmp [ebp+0x10],0       ; arg1->[+0x10] 必须非空
0087c189  cmp [eax+4],0  / jbe    ; {ptr,len}: len 必须 > 0
```

- 基础逻辑:`[ebp+8]` vs `[ebp+0xc]` 与 `esi`(上限)比较(与 `0x87D5A0` 同构,但**独立函数**)。
- 宽度:按 TDR `sizeinfo` 元数据逐元素解码,`sizeinfo_size` 可变(见 §3.4 诊断串)。
- **不做 allocate**:输入缓冲由调用者提供(044 BE-07 结论,本任务复核成立)。

### 2.3 语义证据

诊断串 xref `lib_src\tdr\tdr_net.c`(`VA 0x00D9F060`)出现在 **`0x87C365`**;
同族 net-buffer/host-buffer 诊断串覆盖该函数全体的边界检查分支。
→ **腾讯 TDR net-buffer 解包器**。**不是** CoD netfield(`DIRECT_STATIC`)。

---

## 3. `0x87D5A0`(TDR 解包路径 2)

### 3.1 边界与调用者

- 入口 `0x87D5A0`:`mov eax,0x180c; call 0xC43280`(约 6.2 KB 栈帧)。
- 直接调用者 **4 个,全部在 TQOS `0x85Dxxx`**:
  `0x85D3DB`/`0x85D418`(`0x85D3A0` QOS 包解包)、`0x85D9B5`/`0x85D9F7`(`0x85D870` TQOS 收包)。

### 3.2 参数与前提

```
0087d5b9  mov ebx,[esp+0x181c]   ; arg3 = {data,len}
0087d5c1  mov ebp,[esp+0x1818]   ; arg1 = 描述符对象
0087d5c9  mov edi,[esp+0x1820]   ; arg4 = {out,len}
0087d5ec  test ebp,ebp / je bail ; arg1 != 0
0087d5f4  cmp [ebp+0x10],0 / je  ; arg1->[+0x10] != 0
0087d5fe  test ebx,ebx / je bail ; arg3 != 0
0087d60f  mov esi,[ebx]           ; ptr
0087d619  mov eax,[ebx+4]         ; len  -> 必须 != 0
0087d628  mov edx,[edi] / test    ; arg4: ptr,len 均非 0
```

### 3.3 分支与值域

- 边界:`[ebp+8] < ecx` 或 `ecx > [ebp+0xc]` → 走错误出口(`0x87ECBC`)。
- 变体分支:`[ebp+0x74]`(版本指示器)非 0 且 `[ebp+0x58] > 上限` → 走**版本化**路径
  (`call 0x87BFD0` 取 meta,`push 0xD9EB88` 报 "expect a_iVersion…")。
- 默认路径与 `0x87C110` 结构相似但**独立**(M-3)。

### 3.4 语义证据

- `0x87EB5A` 引用 `lib_src\tdr\tdr_net.c`;
- `0x87D2EF`/`0x87D3C7` 引用同族 TDR 诊断;
- 出口 `0x87ED1F` 紧邻 `0x87ED70`(scratch 获取器),族内一致。
→ **腾讯 TDR net-buffer 解包器**。

> **归因修正:** 042 判其为 "CoD netfield/delta 反序列化"(`CONFIRMED_DIRECT`)。
> 本任务据 `tdr_net.c` 与 TDR 诊断族**推翻**该归因(见 `02` §1.4.1)。

---

## 4. `0x87ED70` / `0x87EDB0`(共享辅助)

### 4.1 `0x87ED70` — TDR 诊断 scratch 获取器

```
0087ed70  cmp dword ptr [0x196c7e8], 0
0087ed77  push esi
0087ed78  mov esi, 0x196c7f0        ; TLS/静态 scratch 基址
0087ed7d  je  0x87ed91
0087ed7f  mov eax,[0x196c7ec]
0087ed85  call dword ptr [0xca8330] ; 槽值(运行期)=0x116CFC69,提供方模块 UNKNOWN
0087ed8f  mov esi, eax
0087ed91  cmp byte ptr [esi+0x3ff], 0
0087ed98  mov eax, esi
0087ed9c  mov byte ptr [esi+0x3ff], 0
0087eda4  ret
```

- **43 个调用者,全部 `0x87Cxxx`/`0x87Dxxx`/`0x87Exxx`(TDR 族)**。
- 返回 0x400(1024)字节诊断缓冲;**不是**"两个 decoder 共同调用的 dispatch core"(044 已判,本任务复核成立)。

### 4.2 `0x87EDB0` — 有界 `wcslen`

```
0087edb0  mov edx,[esp+8]     ; max
0087edb4  mov ecx,[esp+4]     ; wchar*
0087edba  test edx,edx / je 0x87edce
0087edc0  cmp word ptr [ecx],0 / je 0x87edce
0087edc6  inc eax; add ecx,2; cmp eax,edx; jb loop
0087edce  ret                 ; eax = 长度(上限 max)
```

唯一调用者 `0x87C9B7`(TDR 族内),用于 TDR **宽字符串**解码。**辅助函数,非业务语义。**

---

## 5. `0x879AC0`(TDR 变长长度前缀写入器)

- 入口 `0x879AC0`(`push ebp;mov ebp,esp;sub esp,0x10`),出口 `0x879D8C` 附近。
- 4 个 E8 调用者:`0x8799BC`、`0x879D60`、`0x879F44`、`0x87A1F7`(均在 `0x879xxx`-`0x87Axxx` TDR 区)。
- 行为:把一个整数按 `< 0x80` / `< 0x100` / `< 0x10000` / `< 0x1000000` 分支写成
  `1/2/3/4/5` 字节,前缀 `0x80/0x81/0x82/0x83`(见 `evidence` 中 `0x879B2A`–`0x879B84`)。
- 另有按 `[ebp+0xc]`(元素数)的 `jmp [edx*4+0xC79DA4]` 分派(值域 `> 0x14` 拒绝)。
  **注意(M-2 同类):** 该跳表分派的是 TDR **元素类型码**,不能作为业务消息类型证据。
- **结论:** 这是 TDR 的**长度/度量写入**辅助(`0x87A890` "sizeinfo writer" 的同族),
  **不是**游戏 netfield 读取器。042/043 把它与 netfield 关联,本任务按 TDR 归因收窄。

---

## 6. `0x87BE00` / `0x87BA50`(接收原语)

045 已判定,本任务复核:

| 项 | 结论 |
|---|---|
| 身份 | `[0xCA84E8]=select`(ord18)、`[0xCA84E4]=recv`(ord16)、`[0xCA853C]=WSAGetLastError`(ord111) |
| 结构 | `select` 超时门控(`tv_sec=ms/1000` 魔数 `0x10624DD3`)+ `recv` |
| 错误 | `0x2714=WSAEINTR`、`0x2733=WSAEWOULDBLOCK` |
| 调用者 | `0x87BE00` 仅经 `0x87BA50`(E9 跳板)到达;跳板调用者 `0x85D96E`(TQOS recv)、`0x85E71A`(TQOS dispatch) |
| 归属 | 本任务判**平台层(TQOS)使用**;该原语本身是**通用 socket 原语**,不承载业务语义 |

---

## 7. 语义边界总结(回答"通用能力 ≠ 游戏解析器 ≠ 业务处理器")

```
[通用 socket 原语]      0x87BE00 (select+recv)        —— 无业务语义
        │
[通用容器解包器]        0x87D5A0 / 0x87C110 (TDR)     —— 通用缓冲区解码能力
        │  (TDR 框架,被 TQOS 使用;是否也被游戏使用 = UNKNOWN)
[平台消息解析器]        QOSCSPkg/QOSSSPkg (TQOS)      —— TQOS 业务
        │
[游戏消息解析器]        ?? (现有映像内未闭合)          —— BLOCKED
        │
[游戏业务处理器]        gamestate/configstring/snapshot/opcode 消费者  —— UNKNOWN
```

- 现有映像**已证**第一、二层与 TQOS 三层;
- 第四、五层**未在现有映像内证得**哪怕一个直接消费者;
- 因此 **`0x87C110`/`0x87D5A0` 不得被称作"官方 usercmd/snapshot 解码器"**。

---

## 8. 未知项

| 项 | 状态 | 缺失的最小证据 |
|---|---|---|
| 游戏消息解析器入口 | `UNKNOWN` | 从 `0x865xxx`/`0x876xxx` 收包点到游戏状态消费者的直接数据流 |
| TDR 是否被游戏侧复用 | `UNKNOWN` | 任一非 TQOS 调用者 |
| `0x87ED70` 槽 `0xCA8330` 提供方模块 | `UNKNOWN` | `0x116CFC69` 宿主模块名(不影响本任务判定) |
| 第3节区(`RSize=0x62000`)内容 | `BLOCKED` | 可读的该区快照 |
