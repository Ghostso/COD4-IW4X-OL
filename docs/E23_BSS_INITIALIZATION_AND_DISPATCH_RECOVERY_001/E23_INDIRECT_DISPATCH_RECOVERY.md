# E23 间接分派恢复

## 1. 恢复镜像中的间接调用工具（`.tvm0`）

调用点中反复出现的高地址经节区映射后确认位于 `.tvm0`（VA 0x0D958000..0x0DC11000，可执行）：

| 调用点目标（VA） | RVA | 节区 | 用途（按调用形态） |
|---|---|---|---|
| 0x0DF4A028 | 0xDB4A028 | .tvm0 | 取"帧缓冲"数据指针（`mov ecx,[esi+0xB0]; call`） |
| 0x0DF9AA45 | 0xDB9AA45 | .tvm0 | 分配器（`push size; call`） |
| 0x0DF6216D | 0xDB6216D | .tvm0 | 结构拷贝/构造（`push 0x14; lea; call`） |
| 0x0DF6F97C | 0xDB6F97C | .tvm0 | 字段存储（`push len; lea; mov ecx; call`） |

说明：`.tvm0` 是**可执行区**且有完整磁盘字节（RawSize 0x2B8C00，VirtualSize 0x2B9000），与 `.data` BSS 无关。E-21 曾把 `.tvm0` 描述为"VM 混淆、线性反汇编不可靠"，本轮不改变对该区语义的判断，只确认上述调用的**目标地址与入口形态**。

## 2. 五个目标与间接分派的关系

- 五个目标**自身**不是间接分派目标：全文件对其做 VA/RVA 4 字节指针扫描命中 0/1 次，说明它们没有被放入任何函数指针表。
- 它们由 354 个**直接** `E8` 调用点调用（1+36+96+125+96），而非通过 `FF /2` 间接调用。
- 因此"五个地址是隐藏分派表项"的假设**被证伪**。

## 3. `[edi+0x5F4]` 的间接分派

`0x6AAE70` 成功路径 `0x6AB140` 起的序列：

```asm
6AB140  mov eax,[ebp-0x220]        ; span 长度
6AB146  mov ecx,[edi+0x5F4]        ; 协商对象指针（this）
6AB14C  mov edx,[ecx]              ; vptr
6AB14E  mov edx,[edx+0xC]          ; slot 3（以对象首为 vptr[0]）
6AB151  push eax                   ; arg4: len
6AB152  mov eax,[ebp-0x210]        ; span 缓冲基址
6AB158  push eax                   ; arg3
6AB159  push eax                   ; arg2
6AB15A  lea eax,[ebp-0x50]
6AB15D  push eax                   ; arg1
6AB15E  call edx
6AB160  test al,al                 ; 返回布尔
6AB166  je 0xAAB24D                ; 失败分支
```

- vtable = `0xC5A31C`（`.rdata`，RVA 0x85A31C）。
- vptr[+0xC] 槽 = `0xA87D50`（RVA 0x687D50）。

### slot+3（0xA87D50）语义

```asm
687D50 push ebp; mov ebp,esp
687D53 mov eax,[ebp+8]        ; arg1 -> 临时缓冲
687D58 lea esi,[ecx+0xC]      ; this+0xC
687D5B push esi; push 0x10; push eax
687D61 call 0xACE180          ; 长度/哈希校验（cmp [ecx], len 形态）
687D69 test eax,eax; jne 0xA87D8E (失败->日志 0x43A7C0)
687D6D mov ecx,[ebp+0x14]     ; arg4 长度
687D70 mov edx,[ebp+0x10]     ; arg3
687D73 mov eax,[ebp+0xC]      ; arg2
687D76 push esi; push ecx; push edx; push eax
687D7A call 0xACE1B0          ; 流/缓冲递交
687D82 test eax,eax; jne 失败
687D86 mov al,1; ret 0x10
```

即：`slot+3(this, arg1, arg2, arg3, arg4)` — this 为 `[edi+0x5F4]`，对 `this+0xC`（一个 0x10 字节取数据/摘要）做校验后把 `arg2/arg3` 描述的缓冲（长 `arg4`）递交到 `0xACE1B0`，成功返回 1。

## 4. `[edi+0x5F4]` 的写入者与对象来源

| 位置 | 指令 | 含义 |
|---|---|---|
| 0x6AB9B3 | `mov dword ptr [edi+0x5F4],0` | 清空字段 |
| 0x6AB9E7 | `mov dword ptr [edi+0x5F4],eax` | 写入新对象指针 |
| 0x6AB9D8 | `mov ecx,eax; call 0xA87BA0` | 构造该对象 |

构造器 `0xA87BA0` 写入 vtable `0xC5A31C`。
`[edi+0x5F4]` 的全文件读取点：`0x6AB146`（成功路径）、`0x41DE91`、`0x41DF7A`。

## 5. 与五个目标的关系裁定

- 五个目标与 `[edi+0x5F4]` **同族但不同角色**：它们是 `.text` 低层的"缓冲区 Range/memcpy 与字段分派"辅助；`[edi+0x5F4]` 对象（vtable `0xC5A31C`）是"协商/参数"高阶对象。
- 二者通过对象构造链相邻（`0xA87BA0` 构造器紧邻 `0xA878A0`/`0xA87830` 辅助），但**没有指针边**把五个目标放进该 vtable。
- 因此：**不能**把五个目标当作 `[edi+0x5F4]` 的虚表槽位；E-22 若曾暗示此关系，本轮予以切断。
