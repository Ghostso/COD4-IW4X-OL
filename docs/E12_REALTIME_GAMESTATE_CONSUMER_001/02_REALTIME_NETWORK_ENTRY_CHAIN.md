# 02 — 实时网络入口链 / REALTIME NETWORK ENTRY CHAIN

> 等级：`PROVEN` / `INFERRED` / `BLOCKED`。全部地址为 RVA（模块 `codol2697-static-candidate.bin`，ImageBase `0x400000`）。

---

## 1. 网络 IAT 锚点（PROVEN，PE 导入表）

`_tools/t21_imports.py` 输出：

| 导入 | IAT VA | IAT RVA |
|---|---|---|
| `ws2_32.dll!recv` | `0xBAE490` | `0x7AE490` |
| `ws2_32.dll!send` | `0xBAE4C8` | `0x7AE4C8` |
| `wsock32.dll!recvfrom` | `0xBAE50C` | `0x7AE50C` |
| `wsock32.dll!sendto` | `0xBAE504` | `0x7AE504` |
| `wsock32.dll!select` | `0xBAE4D8` | `0x7AE4D8` |
| `wsock32.dll!ioctlsocket` | `0xBAE4F0` | `0x7AE4F0` |
| `kernel32.dll!ReadFile` | `0xBAE22C` | `0x7AE22C` |
| `kernel32.dll!CreateFileA` | `0xBAE1E4` | `0x7AE1E4` |

**这是“实时网络”与“文件读取”的机器可验证分界锚点（PROVEN）。**

## 2. 收包调用点（PROVEN）

`_data/out_iat_callers.txt`：

| 原语 | 调用点 RVA | 所在函数 |
|---|---|---|
| `recvfrom` | `0x1B0BA1` | `0x1B0430` |
| `recvfrom` | `0x6B4E3C` | `0x6B4DE0` |
| `recvfrom` | `0x775ADE` | `0x775AB0` |
| `recv` | `0x602441` | `0x602430` |
| `recv` | `0x6029BE` | `0x6029A0` |
| `recv` | `0x6052AB` | `0x605220` |
| `recv` | `0x775A6C` | `0x775A50` |
| `recv` | `0x784F7D` | `0x784F60` |
| `recv` | `0x788133` | `0x78772D` |

对应发包：`sendto` 4 处（`0xDFADB`/`0x1B09EF`/`0x6B4C92`/`0x775AA2`）、`send` 5 处。

**结论（PROVEN）：** 实时网络收/发原语调用点已定位；这是网络层的**底锚**。

## 3. 应用层环形缓冲（PROVEN）

客户端在 `[0x743DE9C]` 指向的对象中维护一个 **3 MB 环形缓冲**（基址 `obj+0x8048`）：

| 偏移 | 语义 | 证据 |
|---|---|---|
| `+0x8048` | 环形缓冲基址 | `0x352520`/`0x352551`/`0x35259B`/`0x3525D0` 的 `lea ... +0x8048` |
| `+0x30AF2C` | **写游标** | `0x3524FE`/`0x35252D`/`0x35253B`/`0x352561` |
| `+0x30AF30` | **读游标** | `0x35257E`/`0x3525AD`/`0x3525BB`/`0x3525E1` |

两个原语：

| 函数 | 方向 | 签名 | 关键指令 |
|---|---|---|---|
| `0x3524F0` | **写侧**（src → 环形缓冲） | `(src, len)` | `memcpy(ring+write, src, len)` @`0x352559` |
| `0x352570` | **读侧**（环形缓冲 → dst） | `(dst, len)` | `memcpy(dst, ring+read, len)` @`0x3525D9`，返回 `len` |

两者容量上限 `0x300000`（3 MB），溢出时回绕并把游标清零（`0x35253B`/`0x3525BB`）。

**结论（PROVEN）：** `0x3524F0` 是**接收侧写入器**，`0x352570` 是**消费侧读取器**。

## 4. 读取器安装点（PROVEN）

`[+0x89244]` 为可插拔读取函数指针，全镜像 3 处写入（`_data/out_t27_verify.txt`）：

| 站点 | 值 | 语义 |
|---|---|---|
| `0x35141E` | `0x752570` | 网络读取器 |
| `0x3515D9` | `0x74F090` | demo 读取器 |
| `0x356701` | `0x74F090` | demo 读取器 |

**注意：** `0x352570` 是**读侧**（环形缓冲 → 目标），`0x3524F0` 是**写侧**（源 → 环形缓冲）。二者成对，共享同一环形缓冲。

## 5. 链路状态

| 箭头 | 状态 | 证据 |
|---|---|---|
| `recv/recvfrom` → 收包函数 | **PROVEN** | §2 |
| 收包函数 → 环形缓冲写侧 `0x3524F0` | **BLOCKED** | 8 层内未命中（负搜索，不升级为 REFUTED） |
| 环形缓冲读侧 `0x352570` → `0x3547D0`/`0xA2660` | **PROVEN**（`0x3512A0` 内） | E-11 EV-11-07 |
| 环形缓冲读侧 → `0x350170` | **PROVEN**（`0x8F1D0`/`0x3512A0` 内） | 但路径归属为 demo（见 `01`） |

**链在“收包函数 → 环形缓冲写侧”处中断。** 按任务要求，**停在该层，不补造下游调用关系**。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 实时网络底锚（IAT） | **PROVEN** |
| 收包调用点清单 | **PROVEN** |
| 应用层环形缓冲与读写原语 | **PROVEN** |
| 收包函数 → 环形缓冲的调用边 | **BLOCKED** |
| 环形缓冲 → Gamestate 业务解析 | **BLOCKED**（与 demo 链共享读取器，归属未定） |
