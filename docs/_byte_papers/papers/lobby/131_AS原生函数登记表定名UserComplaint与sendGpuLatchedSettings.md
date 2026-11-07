# 131 · AS_* 原生函数登记表定名：`UserComplaint` 日志器与 `sendGpuLatchedSettings` 控制台命令

> ★★ **137 卷更正（重要）**：本卷 §四 的**名字列整体错位一格**（`as_family_scan` 在 `0x693DD0` 处取 `[f+8]` = **下一条记录**的 COL；真布局是 `[COL][vf0=0x693DD0][vf1=handler]`、步进 **12**）。修正后的名字↔处理器表见 137 §1.1；受影响定名：`0x5D39E0`=**AS_UILog**、`0x5D3C80`=**AS_SetRecommendedSetting**、`0x5D3CA0`=AS_SetTierSetting、`0x5D3CB0`=**AS_SetVideoSetting**、`0x5D3DA0`=AS_IIPS_Response、`0x5D42C0`=**AS_GetServerTime**、`0x5D09C0`=AS_GetPlayListIdForNum、`0x5D0A10`=AS_GetPlayListNumForId、`0x5D0A60`=AS_IsDMZGametype、`0x5D2E70`=AS_CreateRoom、`0x5D2F00`=AS_JoinRoom。另：`configure_mp.csv652..663` 不是「键表」，是 `\x15` 前缀的**诊断消息簇**（137 §5）。

> 承接：[130 · UIPage 页号定性与 UI 遥测派发器四分支](130_UIPage页号定性与UI遥测派发器四分支.md)
> 方法：字节级逆向，权威来源 = 本地客户端镜像 `E:\codol_re\client_image_20261027.bin`（build 1649370 / 3.19），`VA = file + 0x400000`
> 性质：**本卷推翻了 130 卷对 `0x5D39E0` 的函数定性**，并用镜像内建 RTTI 字符串把整族 `AS_*` 原生函数**逐个定名**。

---

## §0 结论速览（八条）

1. **上一轮记的「`0x5D3940` = UIException 日志器」是假函数边界**。它是我从 `0x5D3915` 起反汇编造成的错切副产物。真函数是 `0x5D3790`，`ret 4` 在 `0x5D39D2`，长度 `0x243`。
2. `0x5D39B6 call 0x63FC60`（D 入口）属于这个函数；它发射的事件名**不是** UIException，而是 **`UserComplaint`**（格式串 `0xDC2458`，13 个字段）。
3. 这个函数的**类名**由镜像内建 RTTI 给出：**`.?AVAS_TencentReportBadLanguage@@`**。⇒ 「举报不良言论」UI 动作 → 遥测事件 `UserComplaint`。语义闭环。
4. 镜像里存在 **806 条 12 字节描述符行**（`[0x00693DD0][handler][typeinfo]`，结构定性见 §十三，本卷不把"表 vs 虚表"拍死）：`[0x00693DD0][handler][typeinfo]`，其中 780 行严格步长 12 连续（26 个块）。typeinfo 内嵌 mangled 名 ⇒ **806 个 handler 全部被定名，零猜测**。
5. 该表覆盖镜像内 1446 个 `. ?AV…@@` 名中的 806 个。UI/大厅相关族：`AS_Tencent*`、`AS_IIPS_*`、`AS_JoinRoom`、`AS_QuickMatch`、`AS_SetVideoSetting`、`AS_SetTierSetting`、`AS_SetRecommendedSetting`、`AS_JumpGame`、`AS_GetGroupCounts`、`AS_GetPlaylist*`……
6. **★ 130 卷的关键更正**：`0x5D39E0` 不是「UI 遥测派发器」，它是 **`AS_SetRecommendedSetting`**——Flash 侧「应用推荐设置」的原生回调，4 个 case 是设置类别，三路日志（UIClick/UIPage/UIKeySetting）是**副作用**。
7. `AS_UILog`（`0x8435E0`）= `ret 4` 空实现 ⇒ **腾讯 UILog 钩子在本 build 是关闭的**（零字节函数体）。
8. `AS_IIPS_Response`（`0x5D3CB0`）**不是**遥测，它把 `"sendGpuLatchedSettings\n"` 送进**控制台命令缓冲 `Cbuf_AddText`**；`AS_SetTierSetting`（`0x5D3C80`）写 **`configure_mp.csv`** 硬件档案（键 `configure_mp.csv652..663`，660 缺席）。

---

## §一 起点：`0x5D39B6` 是 D 入口的第几个调用点

129 卷把遥测入队口定为四个：`0x640190`(A)、`0x6404B0`(B)、`0x640FD0`(C)、`0x63FC60`(D)。本卷从 D 入口的调用点反查：

```
python -I tools/ptrref_scan.py --calls 0x63FC60
  target 0x63FC60 : 7 处
```

7 处里有一处落在 `0x5D39B6`。上一轮我就是从这里切进去的。

### 1.1 错切是怎么发生的

我从 `0x5D3915` 开始反汇编：

```
0x5D3915  mov ecx,[eax+0x10]
0x5D3918  mov [esp+0x1c],ecx
0x5D391C  call 0x5ee820
...
0x5D3997  push 0xdc2458
0x5D39A3  push 0x329
0x5D39A9  call 0x774900      ; snprintf
0x5D39B6  call 0x63fc60      ; D 入口
0x5D39D2  ret 4
```

指令流是**自洽**的，于是我把 `0x5D3915` 当成了（或把 `0x5D3940` 当成了）函数入口。

### 1.2 判据：`int3` 填充

```
file 段 0x1D3700..0x1D38E5 内的 `cc` 连续段：只有一处
  VA 0x5D378D  len 3
```

⇒ **上一个函数在 `0x5D378A` 结束（`ret 4`），`0x5D378D..0x5D378F` 是 3 字节对齐填充，`0x5D3790` 才是下一个函数入口。**

而 `0x5D3790` 的开头是标准 MSVC 帧：

```
0x5D3790  55            push ebp
0x5D3791  8bec          mov ebp,esp
0x5D3793  83e4f8        and esp,-8          ← 有 SSE/x87 对齐
0x5D3796  81ecec070000  sub esp,0x7ec       ← 2028 字节局部区
0x5D379C  a140f2e300    mov eax,[0xe3f240]  ← __security_cookie
0x5D37A1  33c4          xor eax,esp
0x5D37A3  898424e8070000 mov [esp+0x7e8],eax
```

★★ **教训：反汇编窗口的起点必须落在函数边界上。** 从函数中部起读，指令可以完全自洽（x86 是变长指令，从任意字节起都能解出一串"合理"的指令），但**帧大小、局部缓冲、参数个数全是错的**。上一轮我把 `push 0x329` 当成了某个 809 字节缓冲，实际上 809 只是这个 2028 字节帧里第二大的一块。

---

## §二 函数 `0x5D3790` 逐段字节解剖

长度 `0x5D3790..0x5D39D2` = **0x243**。`ret 4` ⇒ **一个 4 字节参数**（在 `ebp+8`）。

### 2.1 闸门：账号 ID 必须存在

```
0x5D37AA  mov ecx,[0x84abb08]
0x5D37B3  mov edi,[ebp+8]           ; edi = 参数(UI 元素对象)
0x5D37BA  test ecx,ecx
0x5D37BC  jne 0x5D37CC
0x5D37BE  mov ecx,[0x84abb14]
0x5D37C4  test ecx,ecx
0x5D37C6  je  0x5D39BE              ; ★ 两个都空 → 直接跳到收尾，什么都不发
```

⇒ **`[0x84abb08]`/`[0x84abb14]` 是账号标识；未登录时 `UserComplaint` 静默丢弃。**

### 2.2 账号 64 位 ID

```
0x5D37CC  call 0xb9a0f0
0x5D37D1  mov ecx,[eax+0x20]
0x5D37D4  mov edx,[eax+0x24]        ; 64 位账号 ID
0x5D37DA  mov [esp+0x10],ecx
0x5D37E4  mov [esp+0x14],edx
```

`0xb9a0f0` 与 130 卷 `UIKeySetting` 用的是**同一个取值器**（130 §`0x64138D call 0xb9a0f0`）。两个事件都从 `[+0x20]/[+0x24]` 取 64 位值 ⇒ 同源。

### 2.3 从 UI 元素属性桶取"被举报文本"

```
0x5D37D7  mov eax,[edi+0x10]        ; 属性桶 P
0x5D37DE  mov ecx,[eax+0x4c]
0x5D37E1  shr ecx,6
0x5D37E8  test cl,1                 ; ★ 变体类型标志位 bit6
0x5D37EB  je  0x5D37F4
0x5D37ED  mov edx,[eax+0x50] ; mov ecx,[edx]   ; 间接取值
0x5D37F4  mov ecx,[eax+0x50]                  ; 直接取值
```

`shr 6 / test 1` 这个**变体（variant）内联标志位**在 130 卷的 `UIKeySetting`、本卷 `AS_TencentReportPlayer`（`and 0x8f; cmp 0xa`）里反复出现 —— 它是本引擎属性值的统一表示：低位是类型标签，高 1 位表示值是否间接存放。

### 2.4 ★ 分隔符消毒（本卷最硬的一个字节结论）

```
0x5D37F7  mov eax,ecx               ; src
0x5D37F9  lea esi,[eax+1]
0x5D3800  mov dl,[eax] ; inc eax ; test dl,dl ; jne 0x5D3800    ; strlen
0x5D3807  sub eax,esi               ; len
0x5D380B  test eax,eax ; jle 0x5D3838
0x5D380F  lea ebx,[esp+0x28]        ; dst 基址
0x5D3813  sub ebx,ecx               ; dst - src = 常量偏移
0x5D3815  cmp esi,0x1f4 ; jae 0x5D3838      ; ★ 上限 500 字符
0x5D381D  mov dl,[ecx]
0x5D381F  cmp dl,0x7c ; je  0x5D382e        ; '|'  → 0x3b ';'
0x5D3824  cmp dl,0x0d ; je  0x5D382e        ; CR   → 0x3b ';'
0x5D3829  mov [ebx+ecx],dl
0x5D382C  jmp 0x5D3832
0x5D382E  mov byte [ebx+ecx],0x3b
0x5D3832  inc esi ; inc ecx
0x5D3834  cmp esi,eax ; jl 0x5D3815
0x5D3838  cmp eax,0x1f4 ; jbe 0x5D3847
0x5D383F  mov byte [esp+0x21b],0              ; ★ 截断则补 NUL
```

**⇒ `UserComplaint` 是唯一承载"玩家自由文本"的遥测事件，所以它必须做注入防御：把记录分隔符 `|`(0x7C) 和换行 CR(0x0D) 一律替换成 `;`(0x3B)，并截断到 500 字符。**

★★ **这是整条遥测链上唯一的转义点。** 其它事件（UIPage/UIClick）载荷全是数字，不需要转义。我们**构造服务端解析器时，必须假定 `UserComplaint` 的第 9 字段（`%s`，投诉文本）里可能含任意字符，且只可能不含 `|` 和 CR。**

★ 只处理 CR、不处理 LF —— 说明发送端认为 LF 不会出现（或 LF 已被上游剥掉；参照 129 卷 D 入口本身会剥 `\n`/`\r`）。

### 2.5 第一次格式化（0x29D = 669 字节）

```
0x5D3847  lea eax,[esp+0x28]        ; 消毒后的文本
0x5D384B  lea edx,[eax+1]
0x5D3850..0x5D3855                 ; 再 strlen 一次
0x5D3857  push 0x29d                ; 669
0x5D385C  lea ecx,[esp+0x224]       ; dst
0x5D3863  sub eax,edx               ; len
0x5D3865  push ecx
0x5D3866  push eax
0x5D3867  lea edx,[esp+0x34]        ; src
0x5D386B  push edx
0x5D386C  call 0xb74410             ; ★ 4 参: (src,len,dst,cap) = 安全 strncpy
```

`0xb74410` 是**带长度的拷贝**，不是 snprintf —— 因为它只搬字符，不做格式解释。⇒ **玩家文本不会经过 `%` 解释**。这一点很重要：否则玩家提交 `%n` 就能打崩客户端。

### 2.6 第二次格式化（0x329 = 809 字节）与 13 字段

```
0x5D3882  call 0x5ee820
0x5D3887  cmp eax,2
0x5D388D  sete dl                   ; ★ 布尔 = (状态==2)
...
0x5D3997  push 0xdc2458             ; 格式串
0x5D399C  lea eax,[esp+0x500]
0x5D39A3  push 0x329                ; 809
0x5D39A8  push eax
0x5D39A9  call 0x774900             ; snprintf
0x5D39AE  lea ecx,[esp+0x508]
0x5D39B5  push ecx
0x5D39B6  call 0x63fc60             ; ★ D 入口
```

格式串 `VA 0xDC2458`（`file 0x9C2458`），逐字：

```
UserComplaint|${TIMESTAMP}|%llu|${CODOID(%llu)}|%s|${CODOID(%s)}|%d|%s|%d|%d|%d|%d|${ZONEID(%llu)}|${ZONEID(%s)}
```

**14 个 `|` 分隔字段 = 1 个事件名 + 13 个值。** 逐字段：

| # | 字段 | 来源（本函数内） |
|---|---|---|
| 0 | `UserComplaint` | 事件名，**写死在格式串里** |
| 1 | `${TIMESTAMP}` | 采集器占位符，运行时展开 |
| 2 | `%llu` | 账号 64 位 ID 的高/整值（`[0x84abb08]` 链） |
| 3 | `${CODOID(%llu)}` | CODOID（数值形态） |
| 4 | `%s` | **被举报玩家名/文本**（属性桶 `P+0x50`，已消毒） |
| 5 | `${CODOID(%s)}` | ★ **CODOID 的字符串形态** —— 同一 ID 两种表示并存 |
| 6 | `%d` | |
| 7 | `%s` | |
| 8 | `%d` | |
| 9 | `%d` | |
| 10 | `%d` | |
| 11 | `%d` | |
| 12 | `${ZONEID(%llu)}` | 区服 ID（数值） |
| 13 | `${ZONEID(%s)}` | ★ **区服 ID 的字符串形态** |

★★ `%llu`/`%s` 成对出现（CODOID 一对、ZONEID 一对）⇒ 上报端把**同一个身份值同时以数值和文本两路发出**。这不是冗余：数值路给服务端做索引，文本路给人工审核看。`${CODOID(%s)}` 是本卷新增的语义 —— 129/130 卷没记录过这个占位符。

★ `0x5D392D sete dl / 0x5D397A setne al` 那段把 `flag = (0x5ee820() == 2)` 作为一个 `%d` 打出；`0x5ee820` 在 2.6 节和 2.1 节各调一次（`0x5D391C`），返回值被用两处。

---

## §三 类名从哪来：镜像内建 RTTI 名字串

`UserComplaint` 这个事件名给了我语义，但它没告诉我"这是哪个 UI 动作"。类名在 `.data` 里。

### 3.1 一条 12 字节记录

```
VA 0xDC8958:   D0 3D 69 00 | 90 37 5D 00 | B8 2A DF 00
               0x00693DD0 | 0x005D3790 | 0x00DF2AB8
```

第一项 `0x00693DD0` 在整张表里**反复出现**（806 次）；第二项是 handler 地址；第三项指向一个 0x20 字节的类型描述记录。

### 3.2 类型描述记录与内嵌名字

```
typeinfo 0x00DF2AB8:
  +0x00 00000000
  +0x04 00000000
  +0x08 00000000
  +0x0C 00E6C72C        ← 指向「名字宿主」
  +0x10 00DF2ACC        ← 自指（+0x14）
  +0x14 00000000
  +0x18 00000000
  +0x1C 00000006        ← 恒为 6
```

名字宿主 `0x00E6C72C` 的字节（**注意不是 C 串起点**）：

```
+0x00  dword 0x00D77818      ; 另一个指针
+0x04  dword 0x00000000
+0x08  ".?AVAS_TencentReportBadLanguage@@\0"
```

★★ **`cstr(0xE6C72C)` 返回的是 `b'\x18x\xd7'` —— 因为前 3 字节是 `18 78 D7` 后面跟着一个 NUL。名字在 +8。** 我第一遍就是被这个坑住的：把 `0xE6C72C` 当字符串起点，读出乱码，就以为"这条路不通"。

★ 这与 130 卷 `0xDAE091` 的性质**相反**：那次是真的空串；这次是**结构体头**，名字从 +8 开始。判据：`0xE6C72C` 处读出的 3 字节正好等于它自己 dword 的低 3 字节 ⇒ 是**指针字段**，不是字符串。

### 3.3 定名

```
.?AVAS_TencentReportBadLanguage@@  →  handler 0x005D3790
```

**⇒ `0x5D3790` = `AS_TencentReportBadLanguage`（腾讯·举报不良言论），它发射的遥测事件叫 `UserComplaint`。**

★★ **事件名 ≠ 类名，也不是同一个来源。** 事件名在格式串里（`.rdata` 字面量），类名在 RTTI 里（mangled 名）。两者必须都拿到才能闭合语义：只有类名 → 不知道上报什么事件；只有事件名 → 不知道哪个 UI 动作触发。

---

## §四 806 个 12 字节单元（结构定性见 §十三，本卷不给死）

### 4.1 扫描判据

```
1) 全镜像找 dword == 0x00693DD0
2) 其后 12 字节必须 [0x693DD0][f][t]，f、t 都落在 [0x400000, 0x400000+len)
3) t 的 +0x0C 字段 p 也落在镜像内
4) cstr(p+8) 以 ".?A" 开头
```

`tools/as_family_scan.py`。

### 4.2 结果

```
AS_* 名字串 1446 条      ← 全镜像 .?AV...@@ 总数
12 字节记录命中 806 条
stride 直方图: 12 出现 780 次
blocks: 26 个
  0xDC7F8C..0xDC9030  356 行   ← 主块
  0xDCC9FC..0xDCCC54   51 行
  0xDD832C..0xDDD85C  ...（其余 24 块，2..59 行）
```

★ **806 / 1446 = 55.7% 的 mangled 名被这张表覆盖。** 未覆盖的多是**模板实例**（`?AU?$ListNode@…`）和**lambda 局部类**（`AS_*_SF_Handler@?N??Init@UiCppXxx@@`）—— 它们不是"注册在表里的 handler"，而是被 `Init@UiCppXxx` 现场注册的匿名回调。

这一条很有价值：**1446 个名字里，属于"表内 handler"的只有 806 个；剩下 640 个是 SF 内联 handler，挂在每个 `UiCppXxx` 屏幕类的 `Init` 上。** 这直接解释了 130 卷"页名表不存在"的另一面 —— 见 §十一。

### 4.3 UI/大厅相关族（本卷抽查，逐行）

```
.?AVAS_JoinRoom@@                   0x00DC8904 0x005D2E70
.?AVAS_EnableRoomListEvent@@        0x00DC8910 0x005D2F00
.?AVAS_EnableQuickMatchEvent@@      0x00DC891C 0x005D3270
.?AVAS_QuickMatch@@                 0x00DC8928 0x008435E0   ← ret 4 空实现
.?AVAS_IsLogOnLobby@@               0x00DC8934 0x005D32B0
.?AVAS_TencentSanitizeString@@      0x00DC8940 0x005D3520
.?AVAS_TencentReportPlayer@@        0x00DC894C 0x005D3570
.?AVAS_TencentReportBadLanguage@@   0x00DC8958 0x005D3790   ← UserComplaint
.?AVAS_TencentGetAASRecord@@        0x00DC8964 0x005D3660
.?AVAS_UILog@@                      0x00DC8970 0x008435E0   ← ret 4 空实现
.?AVAS_SetRecommendedSetting@@      0x00DC897C 0x005D39E0   ← ★ 130 卷的"派发器"
.?AVAS_SetTierSetting@@             0x00DC8988 0x005D3C80
.?AVAS_SetVideoSetting@@            0x00DC8994 0x005D3CA0
.?AVAS_IIPS_Response@@              0x00DC89A0 0x005D3CB0
.?AVAS_JumpGame@@                   0x00DC89AC 0x005D3DA0
.?AVAS_GetGroupCounts@@             0x00DC89B8 0x005D3E80
.?AVAS_GetLockedMapsFromPublisher@@ 0x00DC89C4 0x005D41B0
.?AVAS_GetServerTime@@              0x00DC89D0 0x005D41C0
.?AVAS_GetPlayListIdForNum@@        0x00DC89DC 0x005D42C0
.?AVAS_GetPlayListNumForId@@        0x00DC89E8 0x005D09C0
.?AVAS_IsDMZGametype@@              0x00DC89F4 0x005D0A10
```

★★ **`AS_GetPlayListIdForNum` / `AS_GetPlayListNumForId` 是一对互逆函数（`0x5D42C0` / `0x5D09C0`）** —— 122 卷 `playlist` 键的 id↔num 双向映射，在客户端里是**两个 AS 接口**。这条给 122 卷的 playlist 值域补了实现出处。

---

## §五 ★ 更正 130 卷：`0x5D39E0` = `AS_SetRecommendedSetting`

130 卷把 `0x5D39E0` 写成「UI 遥测派发器，四分支 0=UIClick/1=UIPage/2=UIKeySetting/3=通用采样」。

**四分支的归属是对的（130 卷那个反推方法是有效的），错的是函数身份。**

### 5.1 字节证据

```
.?AVAS_SetRecommendedSetting@@  0x00DC897C  0x005D39E0
```

`0x5D39E0` 的函数体 `push ebp; mov ebp,esp; and esp,-8; sub esp,0x34; push esi/push edi; call 0x5ebf90`，然后：

```
0x5D3A0C  mov ecx,[eax+0x10]      ; 类别码
0x5D3A0F  cmp ecx,3
0x5D3A12  ja  0x5D3C40            ; >3 → 走默认分支
0x5D3A18  jmp dword ptr [ecx*4+0x5d3c6c]
```

⇒ **`[obj+0x10]+0x10` 的值域 0..3 是"推荐设置的类别"，不是"UI 事件类型"。**

### 5.2 为什么 130 卷会看错

130 卷的推理是：「这个 switch 的每个 case 都调了一个不同的遥测日志器 ⇒ 它是 UI 遥测派发器」。

**这是从"下游行为"反推"上游身份"。** 一个 Flash 回调在执行时**顺带**打三条日志，并不使它成为"日志派发器"。判据应当是：**函数名由 RTTI/登记表给出，日志调用只是它的副作用。**

★ 130 卷 §八 第 1 条方法论（"跳转表给的是入口集合，不是区间"）依然成立且本卷沿用；错的只是函数定性那一步。

### 5.3 语义重建（推荐设置四类）

| case | 目标 | 日志器 | 记录内容 |
|---|---|---|---|
| 0 | `0x641180` ×2 | **UIClick** | `'%d\|%d\|%s'`（含空串哨兵 `0xDAE091`） |
| 1 | `0x6411E0` | **UIPage** | `'%d'` 页号 |
| 2 | `0x641340` | **UIKeySetting** | `'%llu'` 64 位键位 ID |
| 3 | 无日志器 | 5×`get(0..4)` → `0x477910` | 通用采样 |

`0x5D3A35 mov dword [esp+0x24],0xdae091` 是本卷**第二次**独立确认 `0xDAE091` 是**空串哨兵**（130 卷 §4 的自我更正成立）。

---

## §六 为什么 `0x5D39E0` 的 rel32 调用点 = 0（上一轮悬案）

上一轮 `callsite_finder` 与 `ptrref_scan --calls` 都报 0：

```
target 0x5D39E0 : 0 处 -> NONE
target 0x5D3790 : 0 处 -> NONE
```

**不是工具坏了，是它本来就不被直接调用。**

AS_* 是 **Scaleform ActionScript 外部函数**：Flash 侧按**名字**调用，C++ 侧把名字映射到函数地址，**没有静态 call 边**。`0x5D39E0`/`0x5D3790` 的地址只出现在 `.data` 的登记表里。

★★ **⇒ "0 个 rel32 调用点"对这类函数是正常值，不是"死代码"。** 上一轮我把 `callsite_finder 0x1D3940` 的失败当成工具缺陷去查，方向歪了 —— 真正的解释是**虚/名调用**。

★ 这条修正了 130 卷 §八 第 3c 条的一半：「扫描结果为 0 时先怀疑扫描本身」仍然对，但**要先排除"该目标本来就没有 call 边"这一整类**，否则会一直查一个不存在的 bug。

排查顺序应为：
1. 目标是不是被 `[表]` 引用（`ptrref_scan` 的"疑似 [count][ptr] 表项"分支）→ 是 ⇒ 名/虚调用，停止找 call 边；
2. 否则再怀疑扫描本身。

---

## §七 `AS_UILog` = 空实现（`ret 4`）

```
handler 0x008435E0:  c2 04 00            ret 4
```

在同一张表里 `0x8435E0` 出现 **3 次**：`AS_QuickMatch`、`AS_UILog`，以及 `AS_setdvar`。

★★ **⇒ 本 build 的腾讯 UILog 上报钩子 `AS_UILog` 是空函数体。`AS_QuickMatch` 同样是空实现（快速匹配在本 build 未实现）。**

★ 注意 `AS_setdvar` 也是空 —— **Flash 侧调 `setdvar` 不会真的改 dvar**（对应 122 卷「dvar 只能由服务端 playlist 决定」的一致性证据）。

★ 判据方法：**`c2 04 00` 三字节函数体是"接口占位/禁用"的最强信号**，比"找不到引用"更可靠。

---

## §八 `AS_IIPS_Response`（0x5D3CB0）：控制台命令，不是遥测

### 8.1 函数体

```
0x5D3CB0  push ebp ; mov ebp,esp
0x5D3CB3  mov eax,0x2004 ; call 0xc43280       ; _chkstk, 0x2004 字节栈
0x5D3CBD  mov eax,[0xe3f240] ; xor eax,ebp ; mov [ebp-4],eax   ; cookie
0x5D3CC7  mov eax,[0x333abfc] ; push 0 ; push eax ; call 0x771320
0x5D3CD4  mov ecx,[0x333abec] ; push 0 ; push ecx ; call 0x771320
0x5D3CE5  push 0x81a55a0 ; call [0xca819c]      ; ★ EnterCriticalSection
0x5D3CF0  xor eax,eax ; inc eax
0x5D3CF3  cmp byte [eax+0xdc24cc],0 ; jne 0x5D3CF2   ; strlen("sendGpuLatchedSettings\n")
0x5D3CFC  mov edx,[0x76595ac]      ; cmd_text->cmdsize
0x5D3D02  mov ecx,[0x76595a8]      ; cmd_text->maxsize
0x5D3D09  lea esi,[edx+eax]
0x5D3D0C  cmp esi,ecx ; jl 0x5D3D4d ; ★ 容量检查
0x5D3D13  push 0xdc24cc            ; "sendGpuLatchedSettings\n"
0x5D3D18  push 0xdbcf88            ; ★ "Cbuf_AddText: overflow\ntext: %s\n..."
0x5D3D23  push 0x2000              ; ★ 0x2000 = 8192 上限
0x5D3D29  call 0x774900            ; snprintf
0x5D3D31  push 0x81a55a0 ; call [0xca8190]      ; LeaveCriticalSection
0x5D3D4A  ret 4
```

### 8.2 判定

格式串 `0xdbcf88` 逐字：

```
Cbuf_AddText: overflow
text: %s
length: %d
cmd_text->cmdsize: %d
cmd_text->maxsize: %d
```

★★ **`Cbuf_AddText` 是 IW 引擎的"往控制台命令缓冲追加文本"函数**（IW4X / CoD4X 同名同义）。`cmd_text->cmdsize` / `cmd_text->maxsize` 是它的字段名，直接出现在客户端自己的错误串里。

⇒ **`AS_IIPS_Response` 的行为是：`Cbuf_AddText("sendGpuLatchedSettings\n")`，即把 `sendGpuLatchedSettings` 当一条控制台命令排队，容量上限 0x2000 字节，全程在临界区 `0x81a55a0` 内。**

### 8.3 旁证：名字池

```
VA 0xDC06E4:  ... art_relogin\0 snd_restart\0 sendGpuLatchedSettings\0\0 disconnectwithkeepsess ...
VA 0xDC24CC:  sendGpuLatchedSettings\n\0 vid_restart\n\0
```

★ 0xDC06E4 处它夹在 `snd_restart`、`art_relogin`、`disconnectwithkeepsess` 之间 —— **这是控制台命令名池**。★ 0xDC24CC 处是"带换行、可直接投喂 Cbuf 的完整命令文本"，后跟 `vid_restart\n`（另一个"设置变更后需重启渲染"的命令）。

★ **诚实边界**：我没能定位 `sendGpuLatchedSettings` 的**命令处理器注册项**（全镜像对 `0xDC06E4` 的指针引用只命中一处 `0x9C740B`，经反汇编确认是 x87 浮点代码里的**偶然字节重合**）。⇒ 只能证明"它被当命令排队"，**不能证明它有处理器**。若要证，需在运行时断 `Cbuf_Execute` 看未命中命令的报错。

★ 这同时印证记忆里的「IIPS」链：`enable_iips=0` 会让本体 6 秒必崩；`AS_IIPS_Response` 是 IIPS 回应到达后**刷新被 latch 的 GPU 设置**的钩子。

---

## §九 `AS_SetTierSetting`（0x5D3C80）：`configure_mp.csv` 硬件档案

```
0x5D3C83  83e4f8        and esp,-8
0x5D3C86  6a01          push 1
0x5D3C88  6a00          push 0
0x5D3C8A  e8f170f2ff    call 0x4fad80       ; ★ 写 configure_mp.csv
0x5D3C8F  6a01          push 1
0x5D3C91  e86aa91a00    call 0x77e600
0x5D3C9C  c20400        ret 4
```

`0x4FAD80` 内部：

```
0x4FAD8D  mov eax,[0x81a97d8]
0x4FAD9F  mov ecx,0x11e ; mov esi,0x81a97c0 ; rep movsd   ; ★ 0x11e=286 dword 拷贝
0x4FADB1  cmp eax,0x80 ; jge ...  → [ebp-0x2690] = max(0x80, val+8)
0x4FAE2B  push 0xdbd284        ; "configure_mp.csv"
0x4FAE30  push 0x24 ; call 0x49d3b0            ; find-or-create entry
0x4FAE53  push 0xdbd284 ; push 0xdbd27c        ; ★ "1146 %s"
0x4FAE5F  call 0x4f82e0                        ; ★ 写一行命令文本
```

★★ **`0xDBD27C` = `"1146 %s"`** —— 客户端把硬件档位值写进 **dvar / config 条目 `1146`**。这与 118 卷「5 个 dvar 编号 2486/3265/2489/2574/2500 是 mmstart 数字命名 dvar」是**同一族**：本 build 大量使用**数字名 dvar**，`1146` 就是硬件档位那把。

### 9.1 `configure_mp.csv` 的 11 个键（字节级全表）

`.rdata` VA `0xDBD2AD..0xDBD3F5`，每条以 tag `0x15` 起：

```
0x15 configure_mp.csv652
0x15 configure_mp.csv653
0x15 configure_mp.csv654 %s %i
0x15 configure_mp.csv655 %i
0x15 configure_mp.csv656
0x15 configure_mp.csv657 %i
0x15 configure_mp.csv658 %s %i %i
0x15 configure_mp.csv659 %s
0x15 configure_mp.csv661
0x15 configure_mp.csv662 %g
0x15 configure_mp.csv663 %i
     exec configure_mp.cfg
```

★ **编号 652..663 共 12 个，`660` 缺席 ⇒ 实际 11 个键。** 缺席不是漏扫：全镜像 `configure_mp.csv` 字面量 12 处，逐处前 1 字节核对过（11 处前面是 `0x15`，1 处 `0xDBD284` 是裸名）。

★ 相邻的语义串：`%dx%d`、`r_mode`、`%ix%i`、`tex`、`cpu ghz`、`sys mb`、`tier` ⇒ **这就是硬件上报的字段语义池**：分辨率 × 纹理档 × CPU 主频 × 内存 × 显卡 tier。

| 键 | 格式 | 推断语义（邻居+值域级） |
|---|---|---|
| 652 | 无 | 占位/常量 |
| 653 | 无 | 占位 |
| 654 | `%s %i` | 字符串 + 整数（如 GPU 名 + 显存） |
| 655 | `%i` | 单整数 |
| 656 | 无 | 占位 |
| 657 | `%i` | 单整数 |
| 658 | `%s %i %i` | 串 + 两整数 |
| 659 | `%s` | 分辨率串（邻居 `%dx%d`/`r_mode`） |
| 661 | 无 | 占位（邻居 `tier`） |
| 662 | `%g` | 浮点（邻居 `cpu ghz`） |
| 663 | `%i` | 整数（邻居 `sys mb`） |

★★ **诚实边界**：652/653/656/661 四个**没有格式符**，只能确认"键存在"，不能确认字段数。表里 5 条无格式符的键与 6 条有格式符的键混排 ⇒ **`configure_mp.csv` 的列数是变的，不是固定宽表**。这与 120 卷「容器只保证语法不保证语义」同一条。

★ `0x15` 前缀：这是本镜像 TLV 标签表里 `0x15`（通用通道/字符串）的又一次出现，与 129 卷「12 标签表」的 `0x15` 一致。**⇒ 这张键表本身也是以 TLV 形式编码的**，不是裸字符串数组。

---

## §十 `AS_SetVideoSetting`（0x5D3CA0）

```
0x5D3CA0  e89b6ff2ff   call 0x4fac40
0x5D3CA5  c20400       ret 4
```

`0x4FAC40` 与 `0x4FAD80`（tier 写入器）在**同一个函数族**（`0x4F9C80/0x4FA4A0/0x4FA800/0x4FAC40/0x4FAD80`，全是 `configure_mp.csv` 相关）。

⇒ **`AS_SetVideoSetting` = "应用视频设置"（单值），`AS_SetTierSetting` = "写入整档硬件档案"。二者是同一套配置管线的两个入口。**

★★ **三条 UI 入口的正确分工（本卷定，替换任何旧说法）：**

```
AS_SetRecommendedSetting (0x5D39E0) → 打三条遥测（用户点了"推荐设置"）
AS_SetTierSetting        (0x5D3C80) → 写 configure_mp.csv（652..663）+ dvar 1146
AS_SetVideoSetting       (0x5D3CA0) → 0x4FAC40 应用
AS_IIPS_Response         (0x5D3CB0) → Cbuf_AddText("sendGpuLatchedSettings")
```

---

## §十一 ★ 130 卷「页名不存在」的另一面：`UiCppXxx` 屏幕类名是存在的

130 卷结论：**协议面内不存在页号→页名映射**（穷举 12 段 `{id,name}` 表全非 UI；页号来自运行时 `get(0)`）。

本卷补充：**客户端二进制里确实存在一类"屏幕"命名**，只是它不在 `{id,name}` 形态里：

```
UiCpp* 去重 33 个：
  UiCppMainMenu          UiCppOnboarding        UiCppMatchSelectView
  UiCppChallengesView    UiCppItemListView      UiCppSuggestedLoadoutView
  UiCppNewItems          UiCppNewModes          UiCppUserData
  UiCppViewPanel         UiCppList / ListFilter / ListMutable / ListReadOnly ...
  UiCpp0codo … UiCppGcodo / …Ccodo / …Fcodo     ← 混淆后缀
```

它们出现在 `<lambda>@??Init@UiCppXxx@@` 形态的 RTTI 名里（如 `AS_FinishCharacterStep_SF_Handler@?2??Init@UiCppOnboarding@@`）。

★★ **⇒「页号 → 屏幕类」的映射不是一张表，而是每个 `UiCppXxx::Init` 里逐个注册的 Flash 回调。** 想建立映射，得解 `UiCppXxx::Init` 的函数体，看它注册了哪个页面 id —— **这是可做的**（`0x5D42C0`/`0x5D09C0` 这类小函数就是入口），但本卷没做。

★ 因此 130 卷的定性**只在协议面成立**，不推广到二进制面。本卷把它改写成：

> 「协议面内不存在页号→页名映射」（保持）；
> 「二进制面存在 `UiCppXxx` 屏幕类名，但其与 UIPage 数字页号的绑定需要解 `Init` 函数，尚未做」（新增边界）。

★ 注意 `UiCppXxx codo` 后缀族（`0codo/8codo/9codo/Acodo/Ccodo/Dcodo/Ecodo/Gcodo` 与 `ViewPanelCcodo/Fcodo/Gcodo`）—— `codo` 是本作产品名（Codo/CODOL），这些是**带产品前缀的混淆类名**。**不要把它们当成 8 个不同的真实屏幕**，可能是同一模板的 8 个实例化。

---

## §十二 129 卷 `UIException` 的安置

129 卷记 UIException 在 fn `0x1EB380`，格式 `${ZONEID(%llu)}|%llu|${CODOID(%llu)}|%s`。本卷找到该格式串本体：

```
VA 0xDC413C:  "UIException|%s|%u|${ZONEID(%llu)}|%llu|${CODOID(%llu)}|%s"
ctx:  ... can't load jpeg image data\0\0\0 UIException|...\0\0\0 mp/ime.xml\0\0\0 IME.gfx\0\0\0 codo.commo...
```

⇒ **`UIException` 与 IME（`mp/ime.xml`、`IME.gfx`）在同一个字符串池** ⇒ 它是**输入法/IME 子系统的异常上报事件**，与 UI 事件表无关。

★★ **本卷的 `0x5D39B6` 不是 UIException，那个槽位是 `UserComplaint`。** 上一轮的混淆因此解除：两个都是"UI 相关的日志函数"，但分属不同族（IME 异常 vs 举报文本）。

★ 顺带补出同一池里的事件名：`SkinnedModelExceeded`、`LoadoutChangeEvent`、`UserSettings`、`UIFriendEvent`、`UIFriendList`、`ClanCreat…` —— 与 123 卷遥测词表一致，本卷是**在二进制侧独立复核**。

---

## §十三 共享 thunk `0x693DD0`（诚实标注为未定）

```
0x693DD0  55            push ebp
0x693DD1  8bec          mov ebp,esp
0x693DD3  56            push esi
0x693DD4  8bf1          mov esi,ecx
0x693DD6  c706 a47bdc00  mov dword [esi],0x00DC7BA4      ; ★ 写类型/描述符指针
0x693DDC  e8cf2f1900    call 0x826db0
0x693DE1  f6450801      test byte [ebp+8],1
0x693DE5  740e          je 0x693DF5
0x693DE7  8b0ddc78e700  mov ecx,[0x00E778DC]
0x693DED  8b01          mov eax,[ecx]
0x693DEF  8b5030        mov edx,[eax+0x30]
0x693DF2  56            push esi
0x693DF3  ffd2          call edx                       ; 有条件的析构/回收
0x693DF5  8bc6          mov eax,esi
0x693DF7  5e            pop esi
0x693DF8  5d            pop ebp
0x693DF9  c20400        ret 4
0x693DFC  cc cc cc cc   int3  ← 函数边界确认（0x693E00 是下一个函数）
```

★ 帧形态：`(this=ecx, flag=[ebp+8], 返回 this)`，`ret 4` + 返回 `esi` ⇒ **MSVC 的标量删除析构 shim（scalar deleting destructor）形态**：`mov [esi],vtable; call 0x826db0`（可能是基类析构/成员析构），`if (flag & 1) ::operator delete`（走全局分配器 `[0xE778DC]->[0x30]` 的 free），最后返回 this。

★ 帧形态：`(this=ecx, flag=[ebp+8], 返回 this)`，`ret 4` + 返回 `esi` ⇒ **MSVC 的标量删除析构 shim（scalar deleting destructor）形态**：`mov [esi],vtable; call 0x826db0`（基类析构/成员析构），`if (flag & 1) ::operator_delete`（走全局分配器 `[0xE778DC]->[0x30]`），最后返回 this。

### 13.1 两种读法，我选"不定案"，但把判据摆出来

`0x00DC7BA4` 本身也是一个 12 字节单元：

```
0xDC7BA4:  [0x00693DD0][0x00C3E8A6][0x00DF788C]
typeinfo 0xDF788C 的名字  →  ".?AVParser@XML@GFx@Scaleform@@"
```

**读法 A：两槽虚表（vtable）**

```
[+0x00] slot0 = 虚析构 (0x00693DD0)
[+0x04] slot1 = 该类唯一的虚方法   ← 前面叫的 "handler"
[+0x08] class typeinfo 指针（vtable 之外）
```
支持：`0x693DD0` 的帧形态是标量删除析构 shim，`ret 4` 返回 this，与虚析构槽完全吻合；`mov [esi],0xDC7BA4` 是析构时回写基类 vtable 的标准写法。

**读法 A 的反证（我认为它足够强）**：MSVC 的 RTTI 指针放在**虚表之前**（`vftable[-1]` 指向 CompleteObjectLocator），而这里 typeinfo 在**第 2 个槽之后（+8）**。⇒ **这不是标准 MSVC 虚表布局。**

**读法 B：自定义的"函数描述符行"**

```
[+0x00] 共享函数指针（806/806 相同 = 0x00693DD0）
[+0x04] 该名字对应的实现
[+0x08] 类类型描述符
```
支持：描述符行本来就允许带元数据（typeinfo）在末尾，而虚表不允许。

★★ **⇒ 本卷选读法 B（自定义描述符行），理由就是"+8 处有 typeinfo，虚表不会有"。** 但**读法 A 的动机仍然存在**（`0x693DD0` 是析构 shim），所以我把这条裂缝明写出来：

> **`0x00693DD0` 作为首项出现在全部 806 行里，而它自己析构时写 `[esi]=0xDC7BA4`（XML::Parser 那一行）。**
> 若它是"公共回收 shim"（AS 对象都是同一模板、同一套回收），则 806 行共用首项**完全可解释**；
> 若它是"XML::Parser 专用析构"，则矛盾。
> **本卷不做定案** —— 要定案需统计全镜像 `slot0` 的取值分布 + 反汇编 `0x826db0` 与 `[0xE778DC]->[0x30]`。本卷没做。

★★ **不论哪种读法，§六 的答案都成立且更强**：`0x5D3790` 是某个类对象的**一个方法**，只能经"对象/描述符 → 函数指针"间接调用 ⇒ **不会有 `E8 rel32` 指向它**。若读法 A 成立，那就是虚调用；若读法 B 成立，那就是"按名字从描述符表取函数指针再 `call eax`"。**两种情况下 `callsite_finder` 返回 0 都是正确结果，而不是工具坏了。**

★ 已经**与读法无关**、确定成立的部分：
1. 806 行的 `[+0x04]` ↔ typeinfo 名字对应关系 **806/806 自洽**，且**手工核对了三例**（`0x5D3790`/ReportBadLanguage、`0x5D3570`/ReportPlayer、`0x5D39E0`/SetRecommendedSetting），语义都对得上；
2. 这些行在 `.data` 里**成片连续**（780/806 严格步长 12，26 个块）—— 是编译器批量布局的形态，不是手写注册数组；
3. 全镜像共 **1447** 个 typeinfo 结构（每个 `. ?AV…@@` 名一个），其中 **806** 个被这种 12 字节行引用；其余 641 个是模板实例/局部类（`?AU?$ListNode@…`、`AS_*_SF_Handler@?N??Init@UiCppXxx@@`），**没有独立行**。

★★ **⇒ 「806」不是"注册了多少个函数"，而是"有多少个小类各带一条描述符"。** 130 卷想找的"UI 与 C++ 的绑定表"，答案不是一张表，而是**按类分散的描述符/虚表单元**。

---

## §十四 诚实边界（本卷没做到的）

1. **`AS_*` 的"名字→地址"派发机制未定位。** 我证明了它们没有 rel32 call 边、地址在登记表里，但没找到"Flash 送字符串 → 查表 → 调 handler"的那段代码。（可能是 Scaleform `GFx` 的 `GFxExternalInterface` 按名查表；对照 IW4X 无此机制 —— 这是腾讯自研的 AAS 面。）
2. **`sendGpuLatchedSettings` 的处理器注册项未找到**（见 §8.3）。只证"被当命令排队"。
3. **`configure_mp.csv` 652/653/656/661 四键的字段数未定**（无格式符）。
4. **`UiCppXxx` → UIPage 数字页号的绑定未解**（需逐个解 `Init`）。
5. **`0x693DD0` 的语义未定**（§十三 读法 A/B 并列，本卷选 B 并给出反证，但不拍死）；**12 字节行的"虚表 vs 描述符行"也未拍死**。
6. `UserComplaint` 第 6..11 六个 `%d` 字段的**逐字段语义未定**（本函数内多来自 `[esp+0x1c]/[esp+0x18]/[esp+0x30]` 三处，但寄存器复用导致无法逐一对齐）。要定它们必须看 Flash 侧 `AS_TencentReportBadLanguage` 被传了几个参数。
7. 所有结论**只对本镜像（3.19 / 1649370）成立**。`AS_*` 是腾讯自研面，**IW4X / CoD4X 没有对应物，ol-mod 也不覆盖（它是 3.3.3.3）**——本卷因此**没有可用的外部对照**，全部证据来自本地镜像。**按权威层级，本卷证据是最强一级（本地逆向）。**

---

## §十五 本卷工具

| 工具 | 用途 | 本卷是否新建 |
|---|---|---|
| `tools/as_family_scan.py` | 806 行 `[0x693DD0][fn][typeinfo]` 扫描 + 内嵌 `. ?AV…@@` 定名 | **新建** |
| `tools/ptrref_scan.py --calls` | rel32 调用点（`next_insn+rel32==target`） | 沿用 |
| `tools/callsite_finder.py` | 反推调用点；本卷发现它对**表内函数**会返回 0，且这是**正确结果**（见 §六） | 沿用 |
| `tools/dis_640fd0.py` | 反汇编，**入口必须给函数边界**（§一） | 沿用 |
| `tools/rawdump.py` | 原始字节多解（`0xE6C72C` 的 +8 名字靠它） | 沿用 |
