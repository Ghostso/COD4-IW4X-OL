# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

W("03_CALLER_AND_DATAFLOW_AUDIT.md", """# 03_CALLER_AND_DATAFLOW_AUDIT — 调用链与数据流审计

**镜像:** S-IMG `17cef6e0…`。**方法:** 043 独立 E8/imm32 扫描 + 函数边界(CC 填充)归属 + 字符串数据流归属。
**证据:** `evidence/c_consumer_exhaustive.txt`,`c_caller_attribution.txt`,`c_tqos_and_chain.txt`,`c_tqos_scope.txt`,`c_shared_core_and_varint.txt`。

---

## 1. 三个解码器入口的**全部**直接引用(已覆盖 `.text` 全段)

| 目标 RVA | 直接 `E8` 调用者 | imm32 数据/vtable 引用 |
|---|---|---|
| `0x87A890`(长度编码写入器) | `0x879CE3` | **0** |
| `0x87AA40`(第二写入器) | `0x879CC7` | **0** |
| `0x87C110`(解码器#1) | `0x85D49D` | **0** |
| `0x87D5A0`(解码器#2) | `0x85D3DB`,`0x85D418`,`0x85D9B5`,`0x85D9F7` | **0** |
| `0x87BE00`(读包原语) | **0**(仅经 thunk `0x87BA50`) | 0 |
| `0x87BA50`(读包 thunk) | `0x85D96E`,`0x85E71A` | 0 |

> **注意**:`imm32 refs = 0` 表示**未在已覆盖 `.text` 内发现函数指针表项**,**不等于**"无间接调用者"
> (间接调用/未覆盖节区无法排除)。

---

## 2. 调用者的**函数归属**(CC 填充边界)

| 调用者 | 所属函数入口 | 归属 |
|---|---|---|
| `0x879CE3` / `0x879CC7` | `0x879AC0` | netfield 长度/序列化族(`0x879xxx`) |
| `0x85D49D` | `0x85D430` | **TQOS 族** |
| `0x85D3DB` / `0x85D418` | `0x85D3A0` | **TQOS 族** |
| `0x85D9B5` / `0x85D9F7` / `0x85D96E` | `0x85D5A0` | **TQOS 族**(唯一引用 `udp://%s:%d`) |
| `0x85E71A` | `0x85E6F0` | **TQOS 分派器** |

### 2.1 关键裁定 —— 唯一可复核的调用者来自 TQOS 模块

- `0x85D5A0` 的调用者链:`0x85DA5B` → 函数 `0x85D5A0`;其上游 `0x85DA90 ← 0x85EC47`(函数 `0x85EB50`)。
- `0x85EB50` **同时**引用 `tqos_create_protohandle err`(`0x985B1C` @`0x85EBD0`)、`calloc err`(`0x985B38` @`0x85EB78`),
  并**调用对象构造器 `0x85D2E0`**(@`0x85EBBB`)。
- `0x85D2E0` 构造器写入字段名 `QOSCSPkg/QOSCSPkgHead/QOSCSPkgBody/QOSSSPkg/QOSSSPkgHead/QOSSSPkgBody`(@`0x85D2F6/0x85D310/0x85D31D/0x85D341/0x85D35A/0x85D36E`)。
- 分派器 `0x85E6F0` 的调用者 `0x85EB16` 位于函数 `0x85E9C0`,**同属该 TQOS 家族**。

**判定(`CONFIRMED`):** 在**已恢复镜像**中,三个解码器入口(`0x87A890/0x87C110/0x87D5A0`)与读包原语的可复核直接调用者
**全部位于 `0x879AC0`(netfield 序列化族)与 `0x85D2E0…0x85EB50`(TQOS 族)** 两处。

> **对 042 的收紧:** 042 把 `0x85E6F0` 判为 TQOS"平台层、非业务"。043 复核如下:
> - **支持 TQOS 归属**:对象字段名、`udp://%s:%d`、`tqos_*` 全部绑定到 `0x85D2E0`/`0x85EB50`,且分派器
>   属于由 `tqos_create_protohandle` 构造的对象。
> - **但 042 的"→ 排除游戏业务"是过度推断**:TQOS 是**可复用的网络序列化框架**;其解码器
>   (`0x87C110/0x87D5A0`)是**通用 net-buffer 原语**,**也可能**被业务层调用。当前镜像**未提供**业务调用者,
>   但**也未证明不存在**。→ 结论应为 **`CROSS_VALIDATED`(TQOS 归属) + `UNKNOWN`(是否另有业务调用者)**,
>   **不是** 042 的"已确认为非业务"。

---

## 3. 输入缓冲数据流(distinguish 真传递 vs 仅状态)

| 引用点 | 是否传递**输入缓冲** | 依据 |
|---|---|---|
| `0x87C7FB`/`0x87C801` | 是(读) | `cmp` 用 `[ebx+0x18]`/`[esp+0x30]` 边界,溢出走 net-buffer 错误 |
| `0x87D60F`~`0x87D632` | 是(读) | 解引用 `[ebx]`/`[ebx+4]`/`[edi]`/`[edi+4]` = `{data,len}` |
| `0x87A917` | 是(写前检查) | `cmp eax,[ecx]`(需要宽度 vs 可用长度) |
| `0x85E75A` | 否 | 只读**消息类型字** `word[esp+6]` |
| `0x85D2E0..` | 否 | 对象构造/字段名绑定 |

**结论:** 现有证据能证明"解码器**接受** `{data,len}` 形式的输入缓冲";**不能**证明该缓冲来自 socket 收包
(见 04)。

---

## 4. 共享核心(两个解码器入口的关系)

```
0x87C110  ── call ──► 0x87ED70  (x23)   缓冲池/临时缓冲获取
          ── call ──► 0x87EDB0  (x1)    UTF-16 长度计数
0x87D5A0  ── call ──► 0x87ED70  (xN)   同上
          ── call ──► 0x87EDB0  (xN)   同上
0x87C110  ──X──► 0x87D5A0   (无调用/无跳转)
0x87D5A0  ──X──► 0x87C110   (无调用/无跳转)
```

**判定:** 两者**独立入口、共享辅助**(`COMMON_CORE` via `0x87ED70`/`0x87EDB0`),**不是** wrapper 关系。

---

## 5. 未闭合边(见 04 详表)

| 边 | 状态 |
|---|---|
| socket/recv → 读包原语 `0x87BE00` | **BLOCKED**(IAT 槽 `0xCA84E8` 在镜像外) |
| 读包原语 → 解码器 `0x87C110/0x87D5A0` | **UNKNOWN**(无直接边;二者经不同调用者) |
| 业务层 → 解码器 | **UNKNOWN**(唯一可复核调用者为 TQOS;业务调用者不可见) |
| 应用层消息类型表 → 分支 | **UNKNOWN**(未定位 in-match 类型表) |
""")
print("wrote 03")
