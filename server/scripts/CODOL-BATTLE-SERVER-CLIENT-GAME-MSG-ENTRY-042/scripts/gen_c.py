# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(name,text): io.open(os.path.join(ROOT,name),"w",encoding="utf-8",newline="").write(text)

W("04_NET_BUFFER_READER.md", """# 04_NET_BUFFER_READER — 游戏网络消息缓冲读取器/解码器

**镜像:** `image_best.bin` SHA256 `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`
**地址约定:** ImageBase `0x400000`,`file_offset = RVA = VA - 0x400000`(034 以 ASCII 串逐一验证)。
**证据等级:** CONFIRMED_DIRECT / CONFIRMED_DATAFLOW。

---

## 1. 决定性证据:net-buffer 诊断串

| RVA | 串 |
|---|---|
| `0x99EE98` | `; net-buffer NOT enough: real_len<%d> sizeinfo_size<%u> net_start<%p> net_end<%p>` |
| `0x99EEF0` | `; string length error: real_len<%d> available_len<%d> net_start<%p> net_end<%p> custom_size<%u>` |
| `0x99EF50` | `; wstring length error: real_len<%d> available_len<%d> net_start<%p> net_end<%p> custom_size<%u>` |
| `0x99EFB8` | `; net-buffer NOT enough: net_start<%p> net_end<%p> unit_size<%u> count<%d>` |
| `0x99F290` | `; string from net-buffer format error: expect last_char_of_string<%d> is null_char<0>… sizeinfo…` |
| `0x99F428` | `; wstring from net-buffer format error: expect last_char_of_wstring<%hu> is null_wchar<0>…` |

这些串以 `%p` 打印 `net_start/net_end`(读游标/缓冲端)、以 `%d/%u` 打印 `real_len/sizeinfo_size/unit_size`。
**语义:** 一个对"网络消息缓冲区"做**变长/sizeinfo 解码**的读取器;边界不足时报错。`sizeinfo_size` 表明
有一个显式的**长度前缀宽度**字段,--标准的网络序列化布局。

---

## 2. `0x87A890` — sizeinfo 宽度 & 剩余长度检查(机器码)

```
0087a890  push ebp
0087a891  mov  ebp, esp
0087a893  push ecx
0087a894  push ebx
0087a895  mov  ebx, [ebp+0xC]          ; count (元素个数)
0087a898  push esi
0087a899  push edi
0087a89a  xor  edi, edi                 ; edi = 累计长度
...
0087a8a5  mov  eax, [ebp+8]            ; unit_size 表
0087a8a8  movzx ecx, word [eax+esi*2]  ; unit_size[i] (16-bit)
0087a8ad  call 0xB44B20                ; sizeinfo 宽度判定 (2/3/4/5)
0087a8c1  call 0xBCD790                ; 该 unit 的实际字节数
0087a8ca  add  edi, eax
0087a8cc  cmp  esi, ebx
0087a8ce  jb   0xC7A8A5
0087a8d3  cmp  edi, 0x80
0087a8d9  jae  0xC7A8EF                ; >=128 -> width 3
0087a8ef  cmp  edi, 0x100
0087a8f5  jae  0xC7A8FC                ; >=256 -> width 4
0087a8fc  cmp  edi, 0x10000
0087a902  jae  0xC7A909                ; >=65536 -> width 5
0087a914  mov  ecx, [ebp+0x14]         ; 剩余/可用长度指针
0087a917  cmp  eax, [ecx]              ; 需要宽度 vs 剩余
0087a919  jbe  0xC7A929                ; 不足则报 net-buffer NOT enough
```

**判定:** 该函数按"元素大小表"累计一个**序列化长度**,再按阈值 128/256/65536 选择
**sizeinfo 编码宽度 (2/3/4/5 字节)**,并与调用者给定的"剩余可用长度"比较。
这正是 netfield/delta 网络布局里的**长度前缀(sizeinfo)**决策,与任意字符串/本地化/font 逻辑不符。

---

## 3. `0x87C110` — 解码器入口 #1

```
0087c110  mov  eax, 0x17F4             ; 大栈帧(>> 常规字符串/UI 函数)
0087c115  call 0xC43280                ; stack probe
0087c11a  mov  eax, [0xE3F240]         ; __security_cookie
0087c11f  xor  eax, esp
0087c121  mov  [esp+0x17F0], eax
0087c128  push ebx
0087c129  push ebp
0087c12a  mov  ebp, [esp+0x1800]       ; 读取栈参数 arg1
0087c131  push esi
0087c132  mov  esi, [esp+0x180C]       ; 读取栈参数 arg3
0087c139  push edi
0087c13a  mov  edi, [esp+0x180C]       ; 读取栈参数 arg4
```

随后(`0x87C700+`)该函数:
- `mov edx,[esi+0x28]; mov ebp,[ebx+0x2C]; add ebp,edx` → 组合 `net_start` 与元素偏移;
- `mov eax,[ebx+0x24]; cmp eax,ebp; jg …` → 边界比较;
- `mov eax,[ebx+8]; cmp eax,1; jle …; sub eax,0x15; je …; dec eax; …` → 按 `[ebx+8]` 的**类型/元素宽度**多路分支;
- 循环 `mov eax,[ebp]; shld/shrd …; mov [edi],ecx; add edi,8; add ebp,8; dec [esp+0x20]; jne` → 按元素**逐项搬运/重排**。

调用者:`0x85D49D`(唯一 rel32 调用点),属 TQOS 族(见 02)。

---

## 4. `0x87D5A0` — 解码器入口 #2(双缓冲参数)

```
0087d5a0  mov  eax, 0x180C
0087d5a5  call 0xC43280
...
0087d5b9  mov  ebx, [esp+0x181C]       ; arg (buffer B)
0087d5c1  mov  ebp, [esp+0x1818]       ; arg (context)
0087d5c9  mov  edi, [esp+0x1820]       ; arg (buffer A)
0087d5ec  test ebp, ebp / je out
0087d5f4  cmp  [ebp+0x10], 0 / je out  ; context 有效性
0087d60f  mov  esi, [ebx]              ; B->data
0087d619  mov  eax, [ebx+4]            ; B->len
0087d628  mov  edx, [edi]              ; A->data
0087d632  mov  eax, [edi+4]            ; A->len
0087d628  ...
```

**判定:** 该函数接收两对 `{data,len}`(典型的"输入缓冲 / 输出缓冲"或"两段消息")并做有效性检查后,
逐字段反序列化。`0x99EFB8` 的 `net_start/net_end/unit_size/count` 串由本族引用。

---

## 5. 与"游戏业务"的关联强度

| 证据 | 说明 |
|---|---|
| `net_start/net_end/sizeinfo_size/unit_size/count` | 网络消息缓冲语义(非 UI/字符串/font) |
| sizeinfo 宽度阈值 128/256/65536 | 变长长度前缀编码 |
| `[ebx+8]` 元素类型多路 + 逐元素搬运循环 | typed element / delta netfield 布局 |
| 入口同时被 TQOS 族调用 | 该缓冲区读取器是**通用网络序列化原语**,被平台层复用;游戏业务层存在同族使用(下游) |

> **重要区分:** `0x87C110/0x87D5A0` 是**读取器/反序列化原语**的证据;它证明客户端**存在**网络消息缓冲解码能力。
> 其**游戏业务调用者/接收点**在镜像未覆盖节区(`0x76…/0x84…`)→ 见 `05/07`。不把 TQOS 调用误判为游戏业务。
""")

W("05_RECEIVE_PATH.md", """# 05_RECEIVE_PATH — 接收路径(socket → recv → message buffer)与 BLOCKED 边界

**镜像:** `image_best.bin`(sha `17ce…f045`),覆盖 `.text 0x1000..0x8a8000` 与 `.rdata/.data 0x8a8000..0xa65000`。

---

## 1. 已确认的读取原语(接收侧下游)

| 步骤 | RVA | 指令/证据 | 等级 |
|---|---|---|---|
| read 调用 | `0x85E71A` | `call 0x87BA50`(thunk → `0x87BE00`) | CONFIRMED_DIRECT |
| read 返回长度 | `0x85E71F..0x85E724` | `add esp,0x10; test eax; jg`(正字节数) | CONFIRMED_DIRECT |
| 消息类型读 | `0x85E75A` | `movzx eax, word [esp+6]` | CONFIRMED_DIRECT |
| 类型分派 | `0x85E75F..0x85E767` | `sub eax,2; je …; sub eax,2; jne …` | CONFIRMED_DIRECT |
| 处理 #1 | `0x85E7B0` | `push ebx; lea edx,[esp+4]; call 0x85E4F0` | CONFIRMED_DIRECT |
| 处理 #2 | `0x85E769` | `push edi; push esi; call 0x85E5C0` | CONFIRMED_DIRECT |

> **归属:** 该分派器与其对象(`0x85D2E0` 构造,字段 `QOSCSPkg*`/`QOSSSPkg*`,`udp://%s:%d`,`tqos_*`)
> 属 **TQOS = Tencent QoS 平台层**,**不是**游戏 netchan。此处**仍证明**:客户端在 `.text` 内确有
> "读包 → 取消息类型字 → 分派 → 处理"的完整形状。

---

## 2. 读包原语 `0x87BE00`

```
0087be00  sub  esp, 0x110
...
0087be76  push ecx
0087be77  push 0
0087be79  push 0
0087be7b  lea  eax, [esp+0x20]         ; timeout/overlapped 输出
0087be7f  push eax
0087be80  lea  ecx, [esi+1]            ; socket/handle + 1
0087be83  push ecx
0087be84  call dword ptr [0xCA84E8]    ; 读 API(槽名未在镜像内)
0087be8a  test eax, eax
0087be8c  jns  0xC7BEB5
...
0087bec3  call dword ptr [0xCA84E4]    ; 另一路径
```

**限制:** `0xCA84E8`/`0xCA84E4`/`0xCA853C` 是 IAT 槽,**其值位于镜像未提供的高地址节区** →
无法解析为具体 API 名 → 本边的"recv/socket"具体身份 **BLOCKED**(见 07)。

---

## 3. BLOCKED 边界(精确)

| 项 | 缺失 | 后果 |
|---|---|---|
| `.tp3 #3` `VA 0x00A16000`(VSize `0x0DBB1CC0`) | 镜像仅前 `0x62000` 字节 | 运行期全局(`0x76xxxxxx`/`0xE4xxxxxx`)不可解析 |
| `.tp3 #4/#5` `VA 0x0E5C8000/0x0E5C9000` | 镜像仅部分 | IAT(recv/WSARecv)槽值不可解析 |
| socket/recv 代码 | 可能位于上述节区 | "recv → netchan 缓冲"边未闭环 |

**结论:** 接收点(recv/WSARecv)**本轮 BLOCKED**;不得以 TQOS 读包原语冒充游戏业务接收点。

---

## 4. 解除条件(最小充分)

1. 覆盖 `VA 0x0E5C9000`+ 与 `0x76xxxxxx` 的**完整运行期内存镜像**(只读),用于:
   - 解析 `0xCA84E8/0xCA84E4/0xCA853C` 的 API 名;
   - 定位调用 `0x87C110/0x87D5A0` 的**非 TQOS** 调用者;
   - 沿 `net_start/net_end` 回追缓冲分配点。
2. 或:在单独授权下做**只读**运行时 API 追踪(不注入/hook)。
""")

print("wrote 04/05")
