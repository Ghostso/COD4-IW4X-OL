# CODOL 设置来源取证报告（641600 / 63E750 / 注册表）

日期：2026-09-25
镜像：`CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
加载基址：`0x400000`（`offset = VA - 0x400000`）
方法：只读静态反汇编（capstone / pefile）+ 只读注册表查询。**未运行游戏，未写注册表，未改文件。**
脚本：

- `CODOLServer\_subagents\_settings_disasm.py`（主镜像反汇编 / xref / dump / string）
- `CODOLServer\_subagents\_settings_tensafe.py`（TenProxy.dll / TerSafe.dll 检查）

---

## 0. 结论速览

| 问题 | 结论 | 性质 |
|---|---|---|
| `0x641600` 是什么 | 从 **TCLS 代理对象**按 Tag ID 读配置并写全局的 `ApplySettings` | 反汇编事实 |
| `[0x82E1580]` 是什么 | `TenProxy.dll!Invoke(0x566)` 返回的 **`CTclsProxy` 对象** | 反汇编事实 |
| 它的数据来源 | **`OpenFileMappingW` + `MapViewOfFile` 读 `TCLS_SHAREDMEMEMORY<pid>` 共享内存** | 反汇编事实 |
| 是否读注册表 | **否**，`TenProxy.dll` 只导入 `GetPrivateProfileIntW`（读 ini），无任何 Reg* API | 反汇编事实 |
| 注册表里有无原始 HOST/PORT | **没有**（本次查询范围内） | 实测事实 |
| 能否还原原始大厅地址 | **不能**，原始值时序性丢失 | 结论 |

**一句话**：`0x641600` 与注册表无关。它读的是腾讯 TCLS 通过**命名共享内存**交接下来的登录/服务器信息；
`dwauth.ini` 与它写的是**同一组全局变量**，两条路是并列而非覆盖关系。

---

## 1. 完整反汇编 `0x641600`（到 `0x641C1A`）

### 1.1 函数级结构

```
00641600  push ebp / mov ebp,esp / sub esp,0x450
00641609  mov eax,[0xe3f240] / xor eax,ebp / mov [ebp-4],eax   ; __security_cookie
00641616  push 0xd40 / push 0 / push 0x331c5c0 / call 0xc42de0  ; memset 静态缓冲 0x331c5c0 (0xD40 B)
00641628  mov ecx,[0x82e1580]                                   ; ★ CTclsProxy 对象
00641631  lea edx,[ebp-0x450]
0064163D  mov eax,[ecx] / mov eax,[eax+0x24] / push edx / push 1 / call eax
00641647  mov ebx,0x10 / mov [0x331c5d4],ebx
00641652  cmp eax,edi(=0) / je 0x641678                        ; 失败路径
0064165C  mov edx,[ecx] / mov eax,[edx+0x28]
00641661  push 0x331c5d4 / push 0x331c5c4 / push 0x16 / call eax ; ID=0x16
...
00641718  call 0xc3c603                                          ; 字符串拼接
00641726  call 0x654ef0                                          ; 结果转存
00641734  mov eax,[edx+0x28] / push 0x331ca70 / push 0 / push 7 / call eax   ; ID=7 (HOST)
0064174B  ... 长度 clamp 到 0x400
0064178C  push 0x331c670 / push 7 / call [eax+0x28]               ; ID=7 第二字段
006417B7  push 0x331caf4 / push 0 / push 0x1b / call [eax+0x28]   ; ID=0x1B
00641803  push 0x331ca74 / push 0x1b / call [eax+0x28]            ; ID=0x1B 第二字段
00641832  mov edx,[edx+0x24] / push eax / push 0x12 / call edx    ; ID=0x12 → len
00641862  mov eax,[eax+0x38] / push edx / push 5 / call eax       ; ID=5 → 数据块
00641896  mov edx,[edx+0x38] / push eax / push 7 / call edx       ; ID=7 → 数据块
006418F8  ... 比较两个长度是否相等
00641963  mov edi,[ebp-0x424]                                     ; 数据长度
006419A8  lea eax,[ebp-0x418]                                     ; 分隔解析缓冲
006419C3  cmp al,0x3b (';') / cmp al,0x3a (':')                   ; ★ 分隔符 = ';' 和 ':'
006419D2  lea eax,[ebp+ecx-0x417] / mov [ebp+edx*4-0x44c],eax     ; 记录每个字段指针
00641A07  cmp edx,9                                               ; ★ 字段数 == 9
00641ACC  cmp edx,7                                               ; ★ 字段数 == 7
00641B59  cmp edx,5                                               ; ★ 字段数 == 5
```

### 1.2 字段数与全局的对应（写入点）

解析把数据串按 `;` / `:` 切成字段，字段指针依次放在 `[ebp-0x44C]`、`[ebp-0x448]`、…（即任务里说的
`[ebp-0x440]`、`[ebp-0x43C]`、… 区域），第一个字段长度放在 `ebx`，第二个字段指针放 `esi`。

三个分支的写入点如下（都是**字符串拷贝** + `atoi`）：

**分支 `字段数==9`（`0x641A07` → `0x641A10`）**

| 顺序 | 源 | 目标全局 | 指令 |
|---|---|---|---|
| 1 | `[ebp-0x44C]` | `0x81A76A8` (HOST) | `0x641A10` `mov edx,0x81A76A8` |
| 2 | `ebx`（第 1 字段长度串） | `0x81A9EC4` (PORT, `word`) | `0x641A22` `call 0xc3c234` / `0x641A2F` `mov word [0x81A9EC4],ax` |
| 3 | `esi`（第 2 字段） | `0xE51184`（另一模块缓冲） | `0x641A27` `mov edx,0xe51184` |
| 4 | `[ebp-0x440]` | `0xE513D4` (`word`) | `0x641A51` `call atoi` / `0x641A56` `mov word [0xe513d4],ax` |
| 5 | `[ebp-0x43C]` | `0x81A7F34`（字段1） | `0x641A62` `mov edx,0x81A7F34` |
| 6 | `[ebp-0x438]` | `0x81A9780` (`word`) | `0x641A81` `call atoi` / `0x641A86` `mov word [0x81a9780],ax` |
| 7 | `[ebp-0x434]` | `0x81A9784` | `0x641A92` `mov edx,0x81A9784` |
| 8 | `[ebp-0x430]` | `0x81A9EC0` (`word`) | `0x641AB1` `call atoi` / `0x641AC0` `mov word [0x81a9ec0],ax` |
| 9 | `[ebp-0x42C]` | `0x81A9EB8`（经 `0xC40233`） | `0x641AB6`..`0x641BC7` `call 0xc40233` / `0x641BB6` `mov [0x81a9eb8],eax` |

**分支 `字段数==7`（`0x641ACC` → `0x641AD5`）**

| 顺序 | 源 | 目标全局 | 指令 |
|---|---|---|---|
| 1 | `[ebp-0x44C]` | `0x81A76A8` (HOST) | `0x641AD5` |
| 2 | `ebx` | `0x81A9EC4` (PORT) | `0x641AEB` `call atoi` / `0x641AF8` `mov word [0x81a9ec4],ax` |
| 3 | `esi` | `0xE51184` | `0x641AF0` `mov edx,0xe51184` |
| 4 | `[ebp-0x440]` | `0xE513D4` | `0x641B13` `call atoi` / `0x641B18` |
| 5 | `[ebp-0x43C]` | `0x81A7F34` | `0x641B24` |
| 6 | `[ebp-0x438]` | `0x81A9780` (`word`) | `0x641B41` `call atoi` / `0x641B50` |
| 7 | `[ebp-0x434]` | `0x81A9EB8`（经 `0xC40233`） | `0x641B56`..`0x641BAE` |

**分支 `字段数==5`（`0x641B59` → `0x641B5E`）**

| 顺序 | 源 | 目标全局 | 指令 |
|---|---|---|---|
| 1 | `[ebp-0x44C]` | `0x81A76A8` (HOST) | `0x641B5E` |
| 2 | `ebx` | `0x81A9EC4` (PORT) | `0x641B70` `call atoi` / `0x641B7D` |
| 3 | `esi` | `0x81A7F34`（注意：这里第 2 串直接进字段1） | `0x641B75` `mov edx,0x81a7f34` |
| 4 | `[ebp-0x440]` | `0x81A9780` (`word`) | `0x641B98` `call atoi` / `0x641B9F` |
| 5 | `[ebp-0x43C]` | `0x81A9EB8`（经 `0xC40233`） | `0x641BA5`..`0x641BAE` |

### 1.3 "type" 值的真实含义

任务里说的 `cmp edx,7` / `cmp edx,5` **不是枚举 type，而是"数据串里被分隔出的字段个数"**：

- `edx` 的初值在 `0x6419BC` `lea edx,[ebx+1]`（即 1），每遇到一个 `;` 或 `:` 就 `inc edx`（`0x6419E0`）。
- 解析循环结束后 `0x641A07` 直接 `cmp edx,9`；不等再看 `cmp edx,7`；再不等看 `cmp edx,5`；都不等直接 `jmp 0x641BBB`（不写任何全局）。
- 因此分支 `9 / 7 / 5` = **配置数据字段数的三种版本**（新格式 9 段、旧格式 7 段、最简格式 5 段）。
  字段越多，能填的全局越多（9 段比 5 段多填 `0x81A9784`、`0x81A9EC0` 等）。

> 这个"按字段数分支"的写法常见于腾讯系配置串的"向后兼容的变长字段"，不是协议 type。

### 1.4 结束动作与返回值

```
00641BBB  mov ecx,[ebp-4] / mov eax,[ebp-0x41C]   ; 返回值 = 成功标志
00641BC8  mov [0x331c5c0],eax                     ; 写回静态状态
00641BCE  call 0xc3c20f                            ; __security_check_cookie
00641BD6  ret
```

紧跟其后的 `0x641BE0` 是**独立函数**（析构/清理）：依次调用
`[vtable+0x1C]`、`[vtable+0x18]`、`[vtable+0x14]`，最后 `mov [0x82e1580],0` 把全局对象指针清空。

### 1.5 调用者是 `SetDefaults` 还是 `ApplySettings`？

全镜像扫 `E8` 相对调用，指向 `0x641600` 的**只有一处**：

```
call 0x641600 at 0x00642739
```

调用点上下文（`0x6426xx`，函数起点 `0x642500`）：

```
00642690  ... esi = 0xdc7148 ("tencent.tlog")      ; 注册回调项
006426A0  mov [0xe9c6858],edi ... [0xe9c6860],0x63f7f0
006426C1  esi = 0xdc7158 ("tencent.antibottest")   ; 注册回调项
006426E5  mov [0x33303b0],0xe9c684c
006426EF  push 0xdc716c ("\") / push 0 / push 0 / push 0xdc7184 ("2989")
006426FD  call 0x770890                            ; 注册 "2989" 相关项
00642705  esi = 0xdc718c ("tencent.testcumulativereward")
0064270A  call 0x4f37a0                            ; 查重复
00642711  jne 0x642739
00642713  ... 把 {回调=0x63f250, 名字="tencent.testcumulativereward"} 挂到链表 0x33303b0
00642739  call 0x641600                            ; ★ 此处调用
0064273E  ... 建/取 TerSafe.dll，GetProcAddress("CreateObj")，call 之
00642787  mov [0x82e1584],eax
```

**结论**：

- 它是 **`ApplySettings`（应用设置）**，不是 `SetDefaults`。
  理由：它不写入任何硬编码默认值，而是**必须先成功拿到 `[0x82E1580]` 非空对象**（`0x641628` 直接解引用，
  失败会在 `0x641652` 走"不写全局"分支），再去读配置；配置不可用时保持全局原值不动。
- 它由 `0x642739` 调用，而 `0x642739` 处于**启动/组件注册阶段**（同一函数还负责注册
  `tencent.tlog`、`tencent.antibottest`、`tencent.testcumulativereward` 回调并创建 TerSafe 对象）。
- 调用者本身被 `0x4A634F`、`0x4A63C8`、`0x6427B8` 三处调用（`0x642500` 是共用入口）。

---

## 2. `[0x82E1580]` 是什么

### 2.1 创建路径（`0x63E750`）

```
0063E750  push ebp / mov ebp,esp / push ecx
0063E754  mov eax,[0x82e157c]          ; 缓存的 HMODULE
0063E760  test eax,eax / jne 0x63E7AA
0063E764  mov edx,0xdc6edc             ; "TenProxy.dll"
0063E770..0063E796  字符串比较（已加载？）
0063E79A  push 0xdc6edc / call [0xca8158]   ; LoadLibraryA("TenProxy.dll")
0063E7A5  mov [0x82e157c],eax
0063E7AA  push 0xdc6eec ("Invoke") / push eax
0063E7B0  call [0xca8150]                   ; GetProcAddress(h,"Invoke")
0063E7B6  test eax,eax / je 0x63E7C8
0063E7BA  lea ecx,[ebp-4] / push ecx / push 0x566 / call eax   ; ★ Invoke(0x566, &out)
0063E7C8  mov eax,[ebp-4] / ... / ret       ; 返回对象指针
```

调用者：`WinMain 0x77EEA5`，紧接 `0x4FCE80`（`0x77EEA0`）之后：

```
0077EEA0  call 0x4FCE80
0077EEA5  call 0x63E750
0077EEAA  mov [0x82E1580],eax
0077EEB1  cmp eax,ebx / je 0x77EEBE
0077EEB5  mov edx,[eax] / mov eax,[edx+4] / call eax    ; ★ 立即调 vtable+0x04（Initialize）
0077EEBE  push 0xdd96b0 / call [0xca8158] / mov [0x8426b00],eax
```

**关键细节**：`WinMain` 拿到对象后立刻调用 `[vtable+0x04]`，也就是 `CTclsProxy::Initialize`
（见 2.4 的字符串证据），说明对象在 `Invoke(0x566)` 里只是构造，真正的共享内存打开发生在 `Initialize`。

### 2.2 `TenProxy.dll` 导出与 `Invoke` 主逻辑

`TenProxy.dll` 只有 **1 个导出**：

```
Invoke  ordinal=1  rva=0x000013E3  va=0x100013E3
```

`0x100013E3` 是跳转存根，真实函数在 `0x10001D70`：

```
10001D70  push ebp / mov ebp,esp / ...
10001D8E  cmp dword ptr [ebp+8],0x566      ; ★ 只处理 0x566
10001D95  jne 0x10001DDD                    ; 其它 ID 直接返回，out 不变
10001D97  push 0x18E4 / call 0x1000D0DE     ; new 0x18E4 字节（= 6372 B）
10001DBC  call 0x100013A2                   ; ★ 构造（→ 0x10005510）
10001DDB  mov [ecx],edx                     ; *out = 对象指针
```

即：**`Invoke(0x566) = 创建 CTclsProxy 实例并回传指针。**

### 2.3 对象布局与 vtable（这是重点）

构造函数 `0x10005510`（`0x100013A2` 的真身）：

```
10005531  ecx = this
10005534  call 0x100013F7                  ; → 0x100057A0（基类/成员构造）
10005539  ecx = this+4 / call 0x10001505    ; → 0x100087B0
1000554B  ecx = this+0x38 / call 0x10001253 ; → 0x10005540
10005559  mov [this+0x00],0x100205D0        ; ★ 主 vtable
10005562  mov [this+0x04],0x100205A0        ; ★ 次 vtable（多重继承第 1）
1000556C  mov [this+0x08],0x1002059C        ; ★ 次 vtable（多重继承第 2）
10005576  mov [this+0x38],0x10020598        ; ★ 第 4 个 vtable（日志组件）
100055B5..10005635  memset 各内部缓冲（0x49C/0x8C/0x1038/0x8B0/0x10BC/0xCB4...）
1000557D  mov [this+0x8AC],0   ; 1000558A  [this+0x18BC],0
1000559A  mov [this+0x18C0],0  ; 1000563B  [this+0x18C4]=0
10005648  mov [this+0x18C8],0  ; 10005652  [this+0x18CC]=0
10005662  mov [this+0x18D0],0  ; 1000566F  [this+0x18D4]=-1
1000567C  mov [this+0x18D8],0  ; 10005689  [this+0x18DC]=0
10005696  mov [this+0x18E0],0
100056A3  call 0x100011EF      ; → 0x100021A0（构造末尾）
100056A8  push 0x1002055C ("CTclsProxy::CTclsProxy()") / lea eax,[this+0x38] / call 0x10001497
```

**主 vtable `0x100205D0` 全槽表**（脚本实测）：

| 槽 | 槽 VA | 指针 | 真身（跳转目标） |
|---|---|---|---|
| +0x00 | 0x100205D0 | 0x10001339 | 0x10006BD0 |
| +0x04 | 0x100205D4 | 0x10001230 | 0x10005E40 ← `Initialize` |
| +0x08 | 0x100205D8 | 0x1000120D | 0x100075F0 |
| +0x0C | 0x100205DC | 0x1000137F | 0x10007980 |
| +0x10 | 0x100205E0 | 0x100014AB | 0x10007A60 |
| +0x14 | 0x100205E4 | 0x100010CD | 0x10007AB0 |
| +0x18 | 0x100205E8 | 0x10001050 | 0x10007B00 ← 任务问的 +0x18 |
| +0x1C | 0x100205EC | 0x100014BF | 0x10006B20 ← 任务问的 +0x1C |
| +0x20 | 0x100205F0 | 0x10001104 | 0x10007CA0 |
| **+0x24** | 0x100205F4 | **0x1000119A** | **0x10007DA0 ← 任务问的 +0x24** |
| **+0x28** | 0x100205F8 | **0x1000107D** | **0x10007EA0 ← 任务问的 +0x28** |
| +0x2C | 0x100205FC | 0x10001078 | 0x10008140 |
| +0x30 | 0x10020600 | 0x10001451 | 0x10008250 |
| +0x34 | 0x10020604 | 0x100013ED | 0x100083B0 |
| +0x38 | 0x10020608 | 0x10001226 | 0x10008510 |

另三个 vtable（按构造函数写入顺序）：

```
vtable 0x100205A0: +0x00 0x100011AE→0x100083B0?  ...  +0x24 0x10001082→0x10007F??  +0x28..+0x2C = 0（纯虚/空槽）
vtable 0x1002059C: +0x00 0x100014E2→0x1000... , +0x24 0x100010F5 , +0x28 0x10001082
vtable 0x10020598: +0x00 0x100011D1 , +0x24 0x100011DB , +0x28 0x100010F5 , +0x2C 0x10001082
```

### 2.4 槽 `+0x24` / `+0x28` 的真身反汇编（★ 任务核心）

跳转表解出：`+0x24 → 0x10007DA0`，`+0x28 → 0x10007EA0`。

**槽 `+0x24` = `0x10007DA0`（`GetDWORD` / `GetBYTE` 取值，`thiscall`）**

```
10007DA0  push ebp / mov ebp,esp / sub esp,0x5c / push ebx,esi,edi
10007DA9  mov [ebp-4],ecx                     ; this
10007DB3  mov eax,[ebp-4] / cmp [eax+0x18C8],0 / je 0x10007E39
10007DBF  mov ecx,[ebp-4] / cmp [ecx+0x18C4],0 / je 0x10007E39
10007DCB  cmp [ebp+0xc],0 / je 0x10007E39     ; 参数2 必须非空
10007DD4  mov eax,[edx+0x18C8]                ; = 块+8（tag 偏移数组）
10007DE3  mov eax,[edx+ecx*4-4]               ; 参数1 索引 → tag 偏移
10007DED  mov edx,[ecx+0x18C4]                ; = 块基址
10007DF3  add edx,[ebp-0x10]                  ; 基址 + tag 偏移
10007DF9  mov eax,[edx] / mov [ebp-0x18],eax  ; 读 tag 的 length 字段
10007E01  cmp dword ptr [ebp-0x18],4
10007E05  jne 0x10007E1D
10007E07  mov [ebp-8],1                        ; 成功
10007E0E  mov edx,[ebp-0x14] / add edx,[ebp-0x18] / mov eax,[ebp+0xc] / mov ecx,[edx] / mov [eax],ecx
10007E1D  push [ebp-0x18] / push [ebp+8] / push 0x10021AD8     ; ★ "[CTclsProxy::GetDWORD]TagNum: %d Length in Memory Wrong[%d]"
10007E31  call 0x1000142E                     ; 写日志（this+0x38 日志器）
10007E39  ...
10007E4B  push 0 / push [ebp-0x1C] / call 0x100014BA   ; 统一善后
10007E62  ret 8
```

**槽 `+0x28` = `0x10007EA0`（同族，带"一次性读取"语义）**

```
10007EA0  ... 与 0x10007DA0 同构（同样查 this+0x18C4 / this+0x18C8）
10007F0D  cmp [ebp+0xc],0 / jne 0x10007F27
10007F13  mov edx,[ebp+0x10] / mov eax,[ebp-0x18] / mov [edx],eax / mov [ebp-8],1   ; 只取长度，不拷贝
10007F27  push [edx] / push 0 / push [ebp+0xc] / call 0x1000D108    ; memcpy(dst, src, n)
10007F40  cmp [ecx+0x18E0],0 / je 0x10008083
10007F83  cmp dword ptr [ebp+8],4 / jne 0x10008004
10007F95  mov [ecx+0x18D8],1
10007FA2  push 0x10021D48                      ; ★ "[CTclsProxy::GetBYTE]Clear once have get QQSignature"
10007FE7  push 0x10021C90                      ; ★ "...Get QQSignature Fail because it only can be get once !"
10008004  cmp dword ptr [ebp+8],5 / jne 0x10008083
10008019  mov [this+0x18DC],1
10008023  push 0x10021C18                      ; ★ "[CTclsProxy::GetBYTE]Clear once have get LoginKey"
10008068  push 0x10021B68                      ; ★ "...Get LoginKey Fail because it only can be get once !"
10008083  jmp/ret
```

这里出现 `tag==4`（QQSignature）和 `tag==5`（LoginKey）两个特殊 ID：**只能成功取一次**，
取过后置 `[this+0x18D8]` / `[this+0x18DC]` 并把共享内存里对应字节清零。这是"凭证一次性消费"语义。

### 2.5 判定：读注册表 / 读 ini / 读内存设置表？

**答：读的是"内存设置表"——具体是 TCLS 交接下来的命名共享内存块。**

证据（按强度）：

1. **导入表硬证据**：`TenProxy.dll` 的导入里**完全没有** `RegOpenKeyEx` / `RegQueryValueEx` / `RegGetValue`
   等任何注册表 API。与配置有关的只有一条 `KERNEL32.dll!GetPrivateProfileIntW`（读 ini）。
2. **`Initialize` 的字符串与 API**（`0x10005E40` → 真实流程）：

```
10005F21  call [0x100263a8] = GetModuleFileNameW
100060EF  call [0x100263a0] = GetCurrentProcessId
10006101  push 0x10020fa0 = "[CTclsProxy::Initialize] GetCurrentProcessId = %d"
10006177  push 0x10020f70 = "TCLS_SHAREDMEMEMORY"
100061B4  call 0x100014CE / 0x10001393 / 0x10001212   ; 拼名 "TCLS_SHAREDMEMEMORY<pid>"
100061CE  call [0x1002639C] = SetLastError
100061DD  push 0xf001f / push 0 / push <name>
100061E2  call [0x10026398] = OpenFileMappingW
1000621E  setne al / mov [this+0x18D4],handle
10006273  call [0x10026394] = MapViewOfFile
10006279  mov [ebp-0xC8C],eax                 ; 映射基址
100062D8  push 0x10020cf0 = "[CTclsProxy::Initialize] MapViewOfFile Success!"
100062E9  mov eax,[edx] / mov [this+0x18D0],eax       ; 块里第 1 个 DWORD（版本/大小）
100062F4  cmp [this+0x18D0],0x40 / jae 0x1000633E
10006309  push 0x10020cc0 = "TCLS"
1000634A  push 0x10020c94 = "TCLS"
10006371  mov [this+0x18C4],edx               ; ★ 块基址 → +0x18C4
10006383  mov [this+0x18C8],eax               ; ★ 块+4   → +0x18C8（tag 表）
100063A1  add edx,[this+0x18C8].4C            ; 计算数据段
100063AA  mov [this+0x18CC],edx
100063D5  call [edx+0x2c]                     ; vtable+0x2C
100063EE  call [edx+0x24]                     ; vtable+0x24 → 0x10007DA0
```

3. **打开映射时的对象名**（字符串 + 调用参数逐字对应）：

```
[CTclsProxy::Initialize] OpenFileMapping TCLS_SHAREDMEMEMORY+%d Success!     (0x10020df0)
[CTclsProxy::Initialize] OpenFileMapping TCLS_SHAREDMEMEMORY+%d fail!Error code = %d   (0x10020ea0)
[CTclsProxy::Initialize] MapViewOfFile Success!                              (0x10020cf0)
[CTclsProxy::Initialize] MapViewOfFile GetLastError = %d                     (0x10020d64)
```

4. **唯一读 ini 的地方与配置无关**：

```
10008DFA  push 0x10021fc8 ("WriteToLogFile") / push 0x10021fec ("Log")
10008E04  call [0x100263bc] = GetPrivateProfileIntW      ; 读日志开关
10008E87  call [0x100263b8] = CreateFileW                ; 打开 teniolog.ini
0x22024   "teniolog.ini"
```

即 `teniolog.ini` 的 `[Log]WriteToLogFile` 只控制日志，与 HOST/PORT 无关。

5. **另有证书校验**（`VerifyCertInfo`，用 `CryptQueryObject`/`CertFindCertificateInStore`），
   属于安全校验，与地址无关。

### 2.6 是否有 reg key 字符串？

**没有。** 对 `TenProxy.dll` 做 ASCII + UTF-16LE 全量字符串扫描，
关键词 `Software\`、`RegOpenKey`、`RegQuery`、`RegGet` **零命中**；
`TerSafe.dll` 里也没有 `Software\` 命中（只有 libcurl/OpenSSL 自带的 `Host:`/`localhost` 等通用日志串）。

所以本节**不存在需要列举的 reg key 路径**。这是"没有"，不是"没找到"。

---

## 3. 只读注册表查询原始输出

查询方式：PowerShell `Get-ChildItem` / `Get-ItemProperty` + `reg query /s /d`（**全部只读**）。

### 3.1 `HKLM\SOFTWARE\WOW6432Node` 子键（关键词相关）

```
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Activision
    → Call of Duty Advanced Warfare   (空)
    → Call of Duty Ghosts             (空)
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Tencent
    → Androws / BackupDownloader / Components / ntcls / PlatForm_Type_List /
      QQ2009 / QQMusic / QQNT / QQPhotoDrawEx / QQPlayer / WeGame
```

### 3.2 `HKCU\Software` 子键（关键词相关）

```
HKEY_CURRENT_USER\Software\Activision
    → Call Of Duty        : EnrollAIK = 2 (REG_DWORD)
    → Call of Duty MWIII  (空)
HKEY_CURRENT_USER\Software\Tencent
    → QQ2009 / QQMusic / qqplayer / WeGame / Androws / bugReport / TgpMiniBrowser /
      Report / CrossFire / ntcls\crossfire / WeChatAppEx / Weixin ...
```

### 3.3 关键命中（**全部与 CODOL 大厅地址无关**）

```
HKEY_CURRENT_USER\Software\Activision\Call Of Duty
    EnrollAIK    REG_DWORD    0x2

HKEY_CURRENT_USER\Software\Tencent\bugReport
    InstallDir = E:\Program Files\Tencent\TGP\apps\COD\helper_base
    ExtRptFile = ...\TGP\apps\COD\helper_base\log\pallas.tlg
HKEY_CURRENT_USER\Software\Tencent\bugReport\TCLSHost
    InstallDir = E:\Program Files\Tencent\TGP\tcls
HKEY_CURRENT_USER\Software\Tencent\bugReport\TGP
    InstallDir = E:\Program Files\Tencent\TGP
HKEY_CURRENT_USER\Software\Tencent\CrossFire
    InstallPath = G:\WeGameApps\rail_apps\CF：穿越火线(2)
    setup       = G:\WeGameApps\rail_apps\CF：穿越火线(2)\TCLS\Client.exe
HKEY_CURRENT_USER\Software\Tencent\ntcls\crossfire
    setup       = d:\wegameapps\cf：穿越火线\TCLS\Client.exe
    InstallPath = d:\wegameapps\cf：穿越火线
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Tencent\ntcls\crossfire
    setup / install / InstallPath = d:\wegameapps\cf：穿越火线\TCLS\Client.exe ...
HKEY_CURRENT_USER\Software\Tencent\TgpMiniBrowser
    main_placement = 1|298|152|1150|692
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Tencent\WeGame\Apps\WGCommonRedist\...
```

### 3.4 关键词搜索结果

```
reg query "HKCU\Software"                 /f "codol"       /s /d  → 0 match
reg query "HKLM\SOFTWARE\WOW6432Node"     /f "codol"       /s /d  → 0 match
reg query "HKCU\Software"                 /f "call of duty"/s /d  → 无 host/port 命中
reg query "HKLM\SOFTWARE\WOW6432Node"     /f "call of duty"/s /d  → 无 host/port 命中
reg query "HKCU\Software\Tencent"         /s /f "codol"           → 0 match
reg query "HKLM\SOFTWARE\WOW6432Node\Tencent" /s /f "codol"       → 0 match
```

全量枚举 `HKCU\Software`、`HKLM\SOFTWARE\WOW6432Node` 后，含
`host` / `ip` / `address` / `port` / `server` / `auth` / `lobby` 语义的 **CODOL 相关值：0 条**。
（`fs_hello.qq.com`、`ctrl.iips.qq.com` 等出现在**文件**里，不在注册表。）

---

## 4. 恢复原始大厅地址的结论

### 4.1 除了 `dwauth.ini`，还有别的地方能提供 HOST/PORT 吗？

**能，但不是静态配置文件。** 反汇编证明存在另一条独立通路：

```
WinMain 0x4FCE80 → 0x63E750 → LoadLibraryA("TenProxy.dll")
                             → GetProcAddress("Invoke") → Invoke(0x566) → new CTclsProxy
WinMain 0x77EEB5 → [vtable+0x04].Initialize
                     → OpenFileMappingW("TCLS_SHAREDMEMEMORY" + pid)
                     → MapViewOfFile → [this+0x18C4] / [this+0x18C8]
0x641600  → [vtable+0x24] GetDWORD / [vtable+0x28] GetInt，按 Tag ID 取值
          → 写入 0x81A76A8(HOST) / 0x81A9EC4(PORT) / 0x81A7F34 / 0x81A9780 /
                 0x81A9EB8 / 0x81A56A4 / 0x81A76E4 + 0x81A9784 / 0x81A9EC0
```

- **写入目标与 `dwauth.ini` 完全相同**（同一组全局）。
- 所以 HOST/PORT 有两个可能来源：**`dwauth.ini`（WinMain 解析）** 与
  **TCLS 共享内存交接块（CTclsProxy 读取）**。
- 谁最终生效取决于运行时谁后写；两条路都写同一批全局，**不是"默认值 vs 覆盖值"关系**。

另有旁路（非大厅）：TCLS `ServerDir` 返回的 `ip` / `virURL` / `url` / `ServerAppData`
（见 `CODOLServer\TCLS_SERVERDIR_ANALYSIS.md`），但这属于 TCLS 目录/业务数据，不是本报告这组全局的直接来源。

### 4.2 注册表里有没有原始值？

**没有。** 本次只读查询范围内：

- 没有任何 `codol` / `使命召唤` 相关键；
- `Activision\Call Of Duty` 下只有一个 `EnrollAIK=2`，与地址无关；
- `Tencent` 下的 `TGP`/`COD` 命中全是**安装路径和崩溃上报路径**（`helper_base`、`pallas.tlg`），不是服务器地址；
- 没有任何 `host`/`ip`/`port`/`auth`/`lobby` 值。

并且从代码层面也只读共享内存/ini，注册表并非本路径的数据源。

### 4.3 能否给出原始 HOST/PORT？

**不能。**

本机全部 `dwauth.ini` 搜索结果：**0 个文件**
（`COD OL\`、`run_codol_001\sandbox*`、`backups\`、`工具\*`、全盘递归均无）。
`TCLS_SHAREDMEMEMORY<pid>` 是**进程运行时对象**，当前无活动进程、也无历史完整转储，
因此其内含的 tag 值（含可能的游戏服 host/port）**已经丢失，无法恢复**。

**没有可抄写的原始 host/port，因此不生成 `recovered_endpoints.json`。**

---

## 5. 附：可复跑命令

```powershell
python CODOLServer\_subagents\_settings_disasm.py disasm 0x641600 0x641C00
python CODOLServer\_subagents\_settings_disasm.py disasm 0x63E750 0x63E930
python CODOLServer\_subagents\_settings_disasm.py disasm 0x4FCE80 0x4FD080
python CODOLServer\_subagents\_settings_disasm.py xrefs 0x641600
python CODOLServer\_subagents\_settings_disasm.py string 0xdc6edc
python CODOLServer\_subagents\_settings_disasm.py string 0xdc6eec
python CODOLServer\_subagents\_settings_disasm.py string 0xddbda8
python CODOLServer\_subagents\_settings_disasm.py string 0xddbdb0

python CODOLServer\_subagents\_settings_tensafe.py exports "COD OL\TenProxy.dll"
python CODOLServer\_subagents\_settings_tensafe.py sections "COD OL\TenProxy.dll"
python CODOLServer\_subagents\_settings_tensafe.py scan "COD OL\TenProxy.dll" "Software\" "RegOpenKey" "RegQuery"
```

TenProxy.dll 关键 VA（基址 `0x10000000`）：

```
0x100013E3  Invoke 存根
0x10001D70  Invoke 主函数（cmp [ebp+8],0x566）
0x100013A2  构造存根 → 0x10005510
0x10005510  CTclsProxy::CTclsProxy()
0x10005E40  CTclsProxy::Initialize（OpenFileMappingW/MapViewOfFile）
0x10007DA0  vtable+0x24（GetDWORD/GetBYTE）
0x10007EA0  vtable+0x28（GetInt/取值拷贝）
0x10008250  vtable+0x30
0x100083B0  vtable+0x34
0x10008510  vtable+0x38
0x100205D0  主 vtable
0x100205A0 / 0x1002059C / 0x10020598  次 vtable
0x10020F70  "TCLS_SHAREDMEMEMORY"
0x10021FC8  "WriteToLogFile"   0x10021FEC "Log"
0x10022024  "teniolog.ini"
```
