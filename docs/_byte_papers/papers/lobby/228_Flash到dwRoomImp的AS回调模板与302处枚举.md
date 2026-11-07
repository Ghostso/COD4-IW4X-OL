# 228 · Flash → `dwRoomImp` 的 AS 回调模板与全量枚举（302 处引用）

> 卷次：228（房间类 · AS 回调链路）
> 方法：`0x7CF850`（`AS_SetReadyState`）反汇编出统一模板 → 全镜像扫 `[0x82E13FC]` 的所有引用
> 结论：**302 处引用，覆盖 `dwRoomImp` vtable 的 vt[3] .. vt[83]**。

---

## §0 统一模板（从 `0x7CF850` 反汇编得出）

```asm
0x7CF853  mov edx, [ebp+8]          ; Flash 传来的 AS3 对象
0x7CF856  mov edx, [edx+0x10]
0x7CF859  mov ecx, [0x82E13FC]      ; ★★★ dwRoomImp 单例（153/166 卷）
0x7CF85F  movzx edx, byte [edx+0x10]; ready 值（0/1）
0x7CF863  mov eax, [ecx]            ; vtable
0x7CF865  mov eax, [eax + 0x84]     ; ★ vt[33] = SendReady 0x6301A0
0x7CF86B  push edx
0x7CF86C  call eax
0x7CF86F  ret 4
```

**模板：**
```
mov  ecx, [0x82E13FC]      ; dwRoomImp 单例
mov  eax, [ecx]
mov  eax, [eax + SLOT*4]   ; 取虚方法
push <参数>
call eax
```

★★★ **`0x82E13FC` = `dwRoomImp` 单例**（153 卷 `0x639D00` 创建、166 卷定名）。

---

## §1 全量枚举

全镜像扫 `0x82E13FC` 的引用 = **302 处**。

| slot | vt 函数 | 出现 | 备注 |
|---|---|---|---|
| `+0x0C` (vt[3]) | `0x62D5D0` | **最多** | 通用派发 |
| `+0x74` (vt[29]) | `0x62FEA0` | 很多 | |
| `+0x5C` (vt[23]) | `0x62FDE0` | 很多 | |
| `+0x10` (vt[4]) | `0x62DA10` | 多 | |
| `+0x84` (vt[33]) | **`0x6301A0`** | 1 | ★ **SendReady** |
| `+0xE8` (vt[58]) | `0x62EF30` | | |
| `+0x68` (vt[26]) | `0x62FDC0` | | |
| `+0x64` (vt[25]) | `0x62FE80` | | |
| `+0x50`/`+0x4C`/`+0x54` | `0x62FD20`/`0x62FCC0`/`0x62FD80` | | |
| … | | | 覆盖 vt[3]..vt[83] |

★ 出现频率最高的 vt[3]（`0x62D5D0`）是**通用派发**（AS 的 `call` 入口）。

---

## §2 关键 AS 回调（已定名）

| AS3 回调 | 函数 | slot | vtable 函数 |
|---|---|---|---|
| `AS_SetReadyState` | `0x7CF850` | vt[33] | **`0x6301A0` SendReady** |
| （前一个） | `0x7CF840` | vt[4] | `0x62DA10` |
| `0x7CF880` | | vt[3] | `0x62D5D0` |
| `0x7CF8D0` | | vt[3] | |
| `0x7CF920` | | vt[3] | |
| `0x7CF970` | | vt[26] | `0x62FDC0` |
| `0x7CFA50` | | vt[25]/vt[37] | |
| `0x7CFB00` | | vt[39] | |
| `0x7CFB80` | | vt[44] | |
| `0x7CFF50` | | vt[17]/vt[30] | |

★★ **`0x7CF8xx ~ 0x7CFFxx` 是一整片 AS 回调区**（对应房间 UI 的各个按钮）。

---

## §3 与既有卷的关系

| 卷 | 内容 | 本卷关系 |
|---|---|---|
| 135/136 | 7 个 View 的 **62 个 Flash 回调全表** | 那是**另一条链**（View 侧）；本卷是**直接 `[0x82E13FC]`** 的 302 处 |
| 147 | `AS_SetReadyState` handler `0x7CF850` | ✅ 本卷确认并给出模板 |
| 150 | `vt[33]` = `0x6301A0` | ✅ 本卷确认（`0x84/4 = 33`） |
| 153/166 | `0x82E13FC` = `dwRoomImp` | ✅ |

---

## §4 本卷确定结论

| 项 | 状态 |
|---|---|
| AS→C++ 模板（5 条指令） | ✅ |
| `0x82E13FC` 引用 = **302 处** | ✅ |
| 覆盖 `dwRoomImp` vtable vt[3]..vt[83] | ✅ |
| `AS_SetReadyState` → vt[33] → SendReady | ✅ |
| `0x7CF8xx~0x7CFFxx` = AS 回调密集区 | ✅ |
| 每个 slot 的完整 AS 名字 | ⬜ 需另扫（AS 注册链） |

---

## §5 对"开局路径"的价值

★★★ 302 处里**没有一处调 vt[0x13C]（`0x632680`）** —— 与 227 卷一致（它是 booking 超时，不是 AS 回调）。

★ **开局按钮的 AS 回调**应在 `0x7CF8xx~0x7CFFxx` 里，对应某个 slot。
**下一轮应把这 302 处按 slot 归好，与本卷的 vtable 表对齐，找到"开始游戏"按钮走的槽。**

---

## §6 方法论

1. **★★★★★ 一个"AS3 回调入口模板"能通过扫同一全局（`0x82E13FC`）一次性枚举全部回调。**
2. **★★★ 从最熟悉的一个回调（`AS_SetReadyState`）反汇编出模板，比从注册表追更快。**
3. **★★ 高频出现的 slot（vt[3]）通常是通用派发，不是具体动作。**
