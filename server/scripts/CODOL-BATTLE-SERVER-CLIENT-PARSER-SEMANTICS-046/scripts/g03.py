# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def W(n,s):
    open(n,"w",encoding="utf-8",newline="\n").write(s); print("wrote",n,len(s))

W("02_045_CHAIN_ATTRIBUTION.md", r"""# 02_045_CHAIN_ATTRIBUTION

**核心工作包 A:** 裁定 045 接收链 `0x85D96E → 0x87BA50 → 0x87D5A0` 的业务归属。
**镜像:** S-IMG `image_best.bin` `17cef6e0…f045`(ImageBase `0x00400000`,`file_off == RVA`)。
**证据等级:** 除显式标注外均为 `DIRECT_STATIC_EVIDENCE`。

---

## 0. 最终裁定

> ### 结论:**`CONFIRMED_PLATFORM_PATH`**(TQOS / 腾讯 QoS 平台层)
>
> `0x85D96E → 0x87BA50(select+recv) → 0x87D5A0` 是**腾讯 TQOS(QoS)子系统的收包链**,
> **不是** CODOL 游戏业务(in-match netchan)的消息解析入口。
> `0x87D5A0` / `0x87C110` 是腾讯 **TDR**(Tencent Data Representation)的通用 net-buffer 解包器,
> 由 `QOSCSPkg / QOSSSPkg` 收包路径调用。

**置信边界:** 本裁定针对**现有恢复映像**中所观察到的该链的全部可证调用者。
在未覆盖节区是否存在其他(游戏)调用者,本任务**不能否定**(见 §6)。

---

## 1. 逐层检查

### 1.1 `0x85D96E` 的函数边界、调用者、被调用者、控制流

| 项 | 结果 |
|---|---|
| 函数起点 | `0x85D870`(`push ebp; mov ebp,esp` @`0x85D870..0x85D871`,随后 `and esp,-8` + `__chkstk 0x9eb4`,**非** `0x85D5A0` 的子例程边界) |
| 函数终点 | `0x85DA81`(`ret`,后接 `0x85DA82..0x85DA8F` 的 `0xCC` 填充) |
| 直接调用者 | `0x85EC01`(E8),位于 **`tqos_create_protohandle`** `0x85EB50` 内 |
| 被调用者(关键) | `0x87BA50`(select+recv thunk)、`0x87D5A0`(×2)、`0x85D2C4`、`0x85D430`、`0x85D500`、`0xC7B8F0` |
| 栈缓冲 | `sub esp` 类 `0x9eb4` 级;接收缓冲 `lea eax,[esp+0x5000]`,长度上限立即数 `0x4EBC` |

**调用序列(机器码连续,`evidence/a10_chain_function.txt`):**

```
0085d941  call dword ptr [0xca84e8]      ; select
0085d951  call 0xc5d2c4                   ; (TQOS 内部,返回值门控)
0085d96e  call 0xc7ba50                   ; -> jmp 0x87be00 (select+recv)
0085d973  mov  esi,eax                    ; recv 长度
0085d9b5  call 0xc7d5a0                   ; TDR 解包 #1
0085d9f7  call 0xc7d5a0                   ; TDR 解包 #2
```

### 1.2 与 TQOS 线索是否处于**同一可证明的数据流**

| TQOS 线索 | 本任务实证 | 位置 |
|---|---|---|
| `udp://%s:%d` | `0x85D870` 函数**唯一**的字符串实参;`push 0xD85AB0` @`0x85D899`;该串全映像仅 2 处 xref:`0x85D7CB` 与 `0x85D89A` | `evidence/a11_tqos_strings.txt` |
| `QOSCSPkg/QOSCSPkgHead/QOSCSPkgBody` | 同族工厂 `0x85D2E0` 用这 3 个名字调 `[0x87BFF0]`;`mov [esi],0xE44458`(vtable) | `evidence/a12_tqos_factory.txt` |
| `QOSSSPkg/QOSSSPkgHead/QOSSSPkgBody` | 同族工厂 `0x85D2E0` 用这 3 个名字调 `[0x87BFF0]`;`mov [esi+0x10],0xE40398` | 同上 |
| `tqos_create_protohandle err` | `0x85EB50`(`tqos_create_protohandle`)失败路径 `push 0xD85B1C` @`0x85EBCF` | `evidence/a13_callgraph.txt` |
| `tqos_get_qosconnd_iplist fail` | `0x85EB50` 内 `push 0xD85AFC` @`0x85EC15` | 同上 |
| `?tqos_find_connd_by_ip fail` | 同族 `0x85Dxxx`/`0x85Exxx` 字符串 | `evidence/a11_tqos_strings.txt` |
| `ied-tqos.qq.com` | 第3节区字符串 `RVA 0x9D98A0`(TQOS 服务端域名) | 全文搜索 |

**同一数据流证明链(全部为直接机器码):**

```
0x35A1C5 ──call──▶ 0x85EB50  "tqos_create_protohandle"
                        │  push 0xD85B1C "tqos_create_protohandle err"
                        ├─ call 0xC7BA90        (建 socket)
                        ├─ call 0x85D2E0        (QOSCSPkg/QOSSSPkg 描述符工厂)
                        └─ call 0x85D870        ("udp://%s:%d" 收包函数)
                                  ├─ call [0xCA84E8] select
                                  ├─ call 0x87BA50 → jmp 0x87BE00 (select+recv)
                                  └─ call 0x87D5A0 ×2   (TDR 解包)
```

**这是 045 想要但未取得的"同一可证明数据流"** —— 045 只证到"recv→长度→0x87D5A0"这条**边**,
本任务证到该边**整体属于** `tqos_create_protohandle` 发起的 TQOS 协议句柄。

### 1.3 `0x87BA50` 的参数来源 / select 超时 / socket 来源 / recv 处理 / 缓冲所有权

| 项 | 045 已证 | 本任务补充 |
|---|---|---|
| 参数 | `arg1=socket, arg2=buf, arg3=len, arg4=timeout_ms` | socket 来自 `[ebx]`(TQOS conn 对象);`buf = lea [esp+0x5000]`(TQOS 函数栈);`len = 0x4EBC`;`timeout = 0` |
| select 超时 | `ms/1000` 魔数 → `struct timeval` | ✅ 复核不变 |
| 缓冲所有权 | 调用者 TQOS 函数的**栈缓冲** | ✅ `0x85D870` 的 `0x9eb4` 栈帧;不跨函数转交,单帧内消费 |
| recv 返回处理 | `esi=返回值`;`<=0` 退出 | ✅ 复核 |

### 1.4 `0x87D5A0` 的输入/游标/分支/返回值/结果去向

| 项 | 结果 |
|---|---|
| 输入 | `arg1` = TQOS conn 描述符对象;`arg2`/`arg3` = `{data,len}` 指针对;`arg4` = 上限 |
| 输入缓冲 | 由**调用者**(TQOS 收包/发包路径)提供,函数内部**不分配**输入缓冲 |
| 游标/分支 | 位置解码器;校验 `net_start < net_end`、`sizeinfo` 宽度、字符串终止符 —— 见 §1.4.1 |
| 返回值 | `>=0` 成功,`<0` 失败(调用点 `test eax,eax; js bail`) |
| 结果去向 | 写回 `arg1` 指向的 **TQOS 描述符对象**;随后在 `0x85D870` 内被 `0x85D340`/`0x85D3A0` 继续处理,或经 `0x85E74E` 进入 `0x85E6F0` 的 TQOS 分派 |

#### 1.4.1 `0x87D5A0` / `0x87C110` 的归属:腾讯 TDR

`0x87D5A0` 与 `0x87C110` 内部引用诊断串 `lib_src\tdr\tdr_net.c`
(`RVA 0x99F060`,`evidence/a14_tdr_strings.txt`),并引用整套 TDR net-buffer 诊断:

```
; net-buffer NOT enough: real_len<%d> sizeinfo_size<%u> net_start<%p> net_end<%p>
; host-buffer NOT enough: host_start<%p> host_end<%p> unit_size<%u> count<%d>
; string from net-buffer format error: expect last_char_of_string<%d> is null_char<0> ...
```

`lib_src\tdr\tdr_net.c` 的 VA xref = `0x87C365, 0x87D2EF, 0x87D3C7, 0x87EB5A`,
**全部落在 `0x87C110` / `0x87D5A0` 函数族内**。→ 这两个 decoder 是 **TDR 序列化框架**的
net-buffer 解包器,**不是** CoD netfield 协议解析器。

> **042 归因修正:** 042 把 `0x87C110/0x87D5A0` 判为 "CoD netfield/delta 反序列化"(`CONFIRMED_DIRECT`)。
> 该归因**被本任务推翻**:它们是腾讯 TDR 的通用解包器。042 依据的"诊断串相邻"是字符串相邻,
> 不构成协议语义证据(任务书明令不足)。

### 1.5 解码后的数据是否流入游戏快照/usercmd/gamestate/configstrings/snapshot

**没有任何直接证据。** 在现有映像内:

- `0x87D5A0` 的 4 个 E8 调用者 `{0x85D3DB, 0x85D418, 0x85D9B5, 0x85D9F7}` **全部**位于 TQOS `0x85Dxxx` 簇。
- `0x87C110` 的唯一调用者 `0x85D49D` 同样在 TQOS `0x85Dxxx` 簇。
- 二者**不含**任何到游戏状态结构(如 `playerstate/gamestate/configstring`)的写指针;
  它们只写 `arg1` 指向的 TQOS 描述符对象。
- 引擎侧的游戏协议串(`gamestateupdate %d`、`CA_GAMESTATE`、`EXE_CONFIGSTRINGMISMATCH`、
  `connectResponse`、`EXE_LOSTRELIABLECOMMANDS` …)其 xref **全部**落在**低地址区**
  (`0x00054xxx`–`0x00376xxx`),**与 `0x87Dxxx` 无任何交叉引用**(见 §5)。

### 1.6 是否存在其他独立接收路径

**存在。** 全部 `ws2_32` 序号槽的间接调用点(`evidence/a15_ws2_iat_usage.txt`):

| 原语 | 调用点(RVA) |
|---|---|
| `select` | `0x6CBC58, 0x6CC022, 0x85D941, 0x85EAE7, 0x8654F4, 0x876AFF, 0x876BB7, 0x87BBDD, 0x87BD40, 0x87BE84` |
| `recv` | `0x6D3DF1, 0x6D437E, 0x6D6C6B, 0x85D2CA, 0x8655CC, 0x876EED, 0x87BEC3` |
| `recvfrom` | `0x7B163C, 0x86563E` |
| `sendto` | `0x7B1492, 0x865602` |
| `socket` | `0x37FC11, 0x6D6D7F, 0x7B18B9, 0x8653DC, 0x86541C, 0x8768DB, 0x87BAF6, 0x87BB06, 0x87BB19` |
| `bind`/`listen`/`accept` | `0x86544A / 0x86546B / 0x86552B`(同一 no-strings 簇) |

`0x87BEC3` / `0x87BE84` **属于 TQOS**。其余至少 **3 组**独立实现:

| 簇 | 代表函数 | 备注 |
|---|---|---|
| `0x6CBC58…0x6D8xxx` | `0x6CBA20`、`0x6D6BC0`、`0x6D4360`(`Recv failure: %s`)、`0x6D41C0`(`Send failure: %s`) | 多个网络包装,含诊断;`0x6D6xxx` 是 CURL 风格(`Immediate connect fail`、`Local Interface %s`) |
| `0x8653xx…0x866xxx` | `0x8653D0/0x865410/0x865440/0x865460/0x8654A0/0x8655B0/0x8655E0/0x865610` | **无任何邻近字符串**;`socket(AF_INET)+bind+listen+accept+select+recv` → **本机监听风格** |
| `0x8768xx…0x877xxx` | `0x8768D0/0x876AB0/0x876B40/0x876DB0/0x876ED0` | **无任何邻近字符串**;`socket+connect+select+recv+send` |

→ **不能**因 TQOS 链属于平台层就断言"客户端没有游戏网络接收路径"。
至少 `0x865xxx` / `0x876xxx` 两条实现**未被本任务定性**,它们是后续取证的首要候选(见 `09`)。

---

## 2. 为什么 045 不能凭"recv 后进通用 decoder"推断游戏业务协议

1. `0x87D5A0` 是**通用 / 共享**的 TDR net-buffer 解包器(§1.4.1),其调用面天然覆盖多个上层子协议;
   "网络字节进入通用解包器"**不等于**"该字节是游戏业务协议"。
2. 045 只证明了**一条边**(recv→长度→`0x87D5A0`),**没有**证明 `0x85D870` 的**上层语义**。
   本任务补上上层后,该函数唯一语义线索是 `udp://%s:%d`,且其入口是 `tqos_create_protohandle`。
3. "函数名/字符串相邻/结构相似"是任务书**明令不足**的定罪方式;045 的推理恰好落在
   "通用解包器 + 相邻"这一档上。

---

## 3. 支持证据清单

| # | 证据 | 位置 | 等级 |
|---|---|---|---|
| A-1 | `0x85D870` 唯一字符串 = `udp://%s:%d` | `evidence/a10_chain_function.txt`, `a11` | DIRECT_STATIC |
| A-2 | `0x85D2E0` 用 `QOSCSPkg*`/`QOSSSPkg*` 6 个名字建描述符 | `evidence/a12_tqos_factory.txt` | DIRECT_STATIC |
| A-3 | 全链入口为 `tqos_create_protohandle` `0x85EB50` | `evidence/a13_callgraph.txt` | DIRECT_STATIC |
| A-4 | `0x87D5A0`/`0x87C110` 引用 `lib_src\tdr\tdr_net.c` + TDR net-buffer 诊断 | `evidence/a14_tdr_strings.txt` | DIRECT_STATIC |
| A-5 | 全部槽位调用点分布(独立接收路径存在) | `evidence/a15_ws2_iat_usage.txt` | DIRECT_STATIC |
| A-6 | 游戏协议串 xref 全在低地址区,与 `0x87Dxxx` 无交叉 | `evidence/a16_game_strings.txt` | DIRECT_STATIC |

---

## 4. 反证与替代解释

| 替代解释 | 裁定 |
|---|---|
| "TDR 解包器可能也被游戏 netchan 复用" | **不能排除**;但**无任何证据**表明游戏 netchan 调用 `0x87D5A0`(4/4 调用者在 TQOS)。保留为 `UNKNOWN`。 |
| "`udp://%s:%d` 只是日志格式串,函数仍是游戏收包" | 该串是**唯一**字符串,且其函数被 `tqos_create_protohandle` 调用、与 `QOSCSPkg` 工厂并列 → 平台层解释占优。 |
| "`0x85D870` 也可能是混合(平台+业务)入口" | 现有映像内**没有任何**业务调用者;判 `CONFIRMED_PLATFORM_PATH`,但**不**宣称全局唯一。 |

---

## 5. 未解决的替代解释 / 未知项

| 项 | 状态 | 说明 |
|---|---|---|
| 游戏业务 netchan 的收包点 | `UNKNOWN` | 现有映像内未把 `0x865xxx`/`0x876xxx` 连到游戏消费者;见 `09` |
| TDR 是否被游戏侧复用 | `UNKNOWN` | 未见游戏调用者,不能否定 |
| `0x85D3A0` / `0x85E6F0` 分派值域 | `REPORT_ONLY`+部分 | 044 记录了 TQOS 信封类型域;非 in-match opcode |
| 未覆盖第3节区是否含业务 | `BLOCKED` | `RSize=0x62000`,超出即不可读 |

---

## 6. 置信边界(必须随结论传播)

- 本裁定**只针对现有恢复映像**(`17cef6e0…f045`)第1/第2节区**已覆盖**的字节。
- "未找到业务调用者"**不**等于"原始客户端不存在该功能"(第3节区与未恢复节区不可读)。
- 该结论**推翻** 042 的 `0x87C110/0x87D5A0 = CoD netfield` 归因,并**收窄** 045 的
  "接收→解码"边为**平台层内部边**。
""")
print("DONE")
