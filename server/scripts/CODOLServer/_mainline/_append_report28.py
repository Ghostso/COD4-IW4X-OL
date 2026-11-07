"""Append section 28 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 28. 复核 §4.6 时发现：`644=1` 一直是观察器注入的（2026-09-29）

编写第二版交接手册、逐条复核 `[req+0x644]` 写入表时发现本轮全部实跑
都有同一个系统性偏差。

### 28.1 全镜像扫描（严谨版，修正了此前的 off-by-one）

对 `+0x644` 的**立即数写**：

```text
00888C18  = 0
00BA325E  = 3
00BA346A  = 0
00BA3657  = 2
00BA3E5D  = 0
```

对 `+0x644` 的**寄存器源写**：

```text
00B8CA10   模块 0xB8… 内（未分析）
00BA299C   = 0（构造）
00BA35EB   = 1，在 0xBA3590 内部，进入时要求 644==0
```

**没有任何 `mov dword [reg+0x644], 1` 的立即数写。**
`0xBA4080`（连接建立路径，`0xBA4114..0xBA4136`）只写
`[ebx+0xC8]=2`（`BA4127`），**不写 `644`**。

### 28.2 `644=1` 的来源

观察器 `--poke-lobby-globals`（AboProbe.cs，`t>=21` 且 `C8==2`）：

```text
写 [req+0x644] = 1
写 [mgr+0x4F8] = 1
输出 POKE_LOBBY_COMPLETE  mgreq644=1 mgr4f8=1
```

本项目**每一轮**打到 `5E8=3` 的运行都带这个 poke
（标准命令里就有 `--poke-lobby-globals`）。

### 28.3 由此产生的更正

```text
· 旧报告 §19 的「644 保持 1（客户端自己写）」是错的
  —— 那是观察器写的
· 644=1 是「0x87 已被处理」的下游状态（0xBA3590 -> 0xBA35EB）
· 客户端自然状态应当是 644=0（构造初值 0xBA299C）
· 观察器把 644 从 0 强推到 1，恰好把 0x83 分支推入
  BA45DB -> BA4463（return 0），也就是本项目观测到的卡点
```

### 28.4 待验证的可证伪预测（优先级最高）

```text
观察器 --poke-lobby-globals 拆成两半：
  保留 host/port 全局填充
  去掉 [req+0x644]=1 与 [mgr+0x4F8]=1
预测：644 保持 0 -> 0x83 走 BA457E..BA45B2（COM 赋值 + [out]=4）
      而非 BA45DB -> BA4463 -> 复位
```

### 28.5 教训（写进手册 §12.5）

```text
「观察器自身改变了被测状态」这类错误最难发现：它不报错、不复位，
只是安静地把一个正确值改错。本项目出现两次：
  1. 早期残留 644:=3 覆盖写（已修）
  2. 644:=1（延续至今，本轮才定位）
每次开 poke 前先问：这个写会不会把状态推离它自然该处的值。
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
